# firebase-alchemy
Firebase backed by sqlalchemy for faster query processing

## Status

Dev: [![Build Status](https://travis-ci.org/newpro/firebase-alchemy.svg?branch=develop)](https://travis-ci.org/newpro/firebase-alchemy.svg?branch=develop)

Master: [![Build Status](https://travis-ci.org/newpro/firebase-alchemy.svg?branch=master)](https://travis-ci.org/newpro/firebase-alchemy.svg?branch=master)

## Why firebase-alchemy

Firebase provides robust and relatively easy to use realtime database. But there is some issues regarding to the database. This repo is designed to solve following problems:

### Problem 1: Hard to design good data structure

If you are in a 24 hours hackathon, or build a quick demo for a startup, any structure for firebase will do. But if you are seriously consider use firebase in your project in a long run, it takes long time to design a good data structure in firebase. **Good structure design** is [officially defined](https://firebase.google.com/docs/database/web/structure-data#best_practices_for_data_structure) in following ways:

*  Reducing retrieve quantity (Avoid nesting data)
* Efficient client download (Flatten data structures)
* Scalability (Create data that scales)

The requirements for good structure design is very hard to accommodate. For example, in the offical document, it use a simple example of building chat message. As you can see, the structure very quickly becomes very messy. Imaging, or rather based on your previous experience, how messy it can be if we are in a complex situation. For another example, in the scalability section, it is required to know the query you need to run beforehand. In the tutorial later in this document, you will see how this repo solve the example of chat message much nicely.

### Problem 2: Slow query speed

Compare to relational db, like sql, firebase have **much slower query speed**, even if you already have good structure in place.

### Problem 3: No Integration with relational database

Firebase does not provide integration with relational database, and a lot of times, it is important to do so. For example, in a web server that provides chat service, the server need to store more than chats, like user info, payments. Without a relational support, it is **slow, expensive, and hard** to store and implement all in firebase and its logic.

### The solution

Firebase-alchemy is designed to solve all problems by build on both sql and firebase, utilize both of their advantages: 

* Process query, structure data, build relationship, enforce integrity by SQL, since it is the best of it.
* Handle client listeners by firebase, since it is the best at it.

This repo is build on libraries:

* [python-firebase](https://github.com/ozgur/python-firebase): python interface for firebase.
* [SQLAlchemy](http://www.sqlalchemy.org/): the best python SQL ORM there is.

## Basic tutorial

In this tutorial, we are going to build a database that store and process user chats. It is required to have basic knowledge about SQLAlchemy. If you do not, please walk through [its basic tutorial](http://docs.sqlalchemy.org/en/latest/orm/tutorial.html). The complete runnable code is in [example.py](./example.py).

The objectives of the database is to store user info, chat groups, and chats, let client fetch more quickly and makes it easily expandable for more functionalities. 

### Data Structure & Operations

Assume we already set up SQLAlchemy session (If u do not know how, check on its tutorial and our example), we start to construct a SQL ORM structure. 

We first need to let it know how to manage our database, by providing reference to SQL session and path to your firebase database.

```python
from firebase_alchemy.manager import Adaptor
adaptor = Adaptor(session=sql_session_reference, firepath='https://[project_name].firebaseio.com')
```

Let us start construct our data schema, first we need a user table. Since user info do not need to store in firebase, it is just a normal sql table schema: 

```python
class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True)
    chats = relationship('Chat',
                         secondary=user_chats,
                         lazy='dynamic')
```

Then we want to add table to store chats, and this table should be build on both SQL and Firebase. We provides a convenient way to help you build the table. Simply build a SQL schema, and inheritance from our FireMix:

```python
from firebase_alchemy.mixin import FireMix
class Chat(Base, FireMix):
    __tablename__ = 'chats'
    id = Column(Integer, primary_key=True)
    name = Column(String)
    users = relationship('User',
                         secondary=user_chats,
                         lazy='dynamic')
```

And we need to declare the many to many table user_chats to link them together, as usual in SQL secondary table fashion.

```python
user_chats = Table('chat_map',
                   Base.metadata,
                   Column('index', Integer, primary_key=True),
                   Column('user_fk', Integer, ForeignKey('users.id')),
                   Column('chat_fk', Integer, ForeignKey('chats.id'))
                   )
```

Now because chat is exists in both SQL and Firebase, we need to assign a manager to help us. Simply construct use our ModelManager class, giving db adaptor that we previously constructed,  your "Chat" class, and optionally you can give a firepath argument to tell it which branch you want it to store, and a validator to enforce how your chat message should looks like.

```python
chat_manager = ModelManager(adaptor, Chat, firepath='chats', validator=['msg', 'who'])
```

Now we are **GOOD TO GO**!

Let us play with it a little bit. First add some users to it.

```python
aaron = User(name='aaron')
bill = User(name='bill')
colin = User(name='colin')
session.add_all([aaron, bill, colin])
session.commit()
```

Then we build some new chat groups. It is time to sit back and let our manager do the work.

```python
chat1 = chat_manager.add(name='Sunday Picnic')
chat2 = chat_manager.add(name='Colin surprise birthday party')
```

The manager automatically record in both sql and firebase, and commit for you, then return the model instance back to you, so you can continue use it in SQL ways.

Because chat1 and 2 are just SQL model object, we can do whatever SQL can do. Now let us add some user to the group using the chat model.

```python
chat1.users.append(aaron)
chat1.users.append(colin)
chat2.users.append(aaron)
chat2.users.append(bill)
session.commit()
```

And run query by SQL:

```python
# fetch queue as fast and easy as sqlalchemy!
print '{} in chat for {}: {} '.format(colin.name, chat1.name, colin in chat1.users)
>>> colin in Sunday Picnic: True
print '{} in chat for {}: {} '.format(colin.name, chat2.name, colin in chat2.users)
>>> colin in Colin surprise birthday party: False
```

And let us secretly discuss about throw Colin a surprise birthday party in chat2, as where it belongs.

```python
# chat about something
chat_manager.push(chat2, {'msg': 'Let us throw colin a suprise party!',
                          'who': aaron.name})
chat_manager.push(chat2, {'msg': 'Yeah agree!',
                          'who': bill.name})
```

Now the chats is stored in firebase, and your clients can see this message in realtime, if they are connected to the endpoint. 

Later we can choose to delete chat2. Chat Manager can do that for you. It will propagate to firebase to delete there first, then delete the model instance.

```python
chat_manager.delete(chat2) # uncomment this to remove chat
```

### Client fetching

For why do client fetching, refer to [Best Practices](#best-practices)

Continue as the example, since the system is build on SQL, it can effectively fetch info from server side and send it to one listening client. 

In this example, Let us say Bill is a client, and he is online to chat. The server can get all bills chat in SQL fashion: 

```python
bill.chats
```

And when bill click on chat2 and start to chat, the server simply tells the client what it should listen to, by fetch the path of chat2 in Firebase. You can use our old friend ChatManager to get the fire:

```python
client_listen_path = chat_manager.get_path(chat2)
```

Then the server can send this path to client to listen to. Client can perform various firebase operations in firebase support JS libraries as before.

## Best Practices

### Servers fetch, clients do read/write

Because we provided push operations, you might tempted to use server to write realtime data to firebase, by using the following client/server workflow, let us call it **workflow 1**:

* Step 1: Client wants to write to a topic
	* issue write request to server
* Step 2: Server deals with the request, by running SQL query
	* Server checks if client is eligible to write in location
	* Server runs SQL query to find out the location of topic
	* Server writes to location
	* Server sends success response to client
* Step 3: Client write operation success

In this workflow, there are several problems:

* Server has to run query for every client write requests.
* Server is waiting for the write to finish, either block or context switch in multi-threading, either way waste the precious server resources.
* All data operations is bottleneck by your server, since your server is normally much less powerful than firebase db server.

**An better alternative workflow** can avoid the problems, let us call it **workflow 2**:

* Step 1: Client wants to **start access** to a topic
* Step 2: Server prepares for client read/write, by running SQL query
	* Server runs SQL query to locate the topic
	* Server check if client is eligible to write in topic
	* Server fetches the firebase path of the topic
	* Server send the path as response to client
* Step 3: Client now can do multiple read/write for a long period of time, directly contact firebase DB without server involvement

The workflow2 looks very good in most of situations, **except one**: If you are required to run some extra server logic before every writes,  you still have to use workflow1. 

For example, if we want to build a amazon store-liked service, charge user with Stripe, and store how many payments are successfully completed in realtime, we write something similar to workflow1 as followings: 

* Step 1: Client send credit card info
* Step 2: Server charges the user and write to Firebase
	* Server issue request to Stripe, wait for result
	* If charge success
		* fetch path to payment topic
		* write to path
		* optionally record this payment in SQL
	* Server send success to client
* Step 3: Client payment success

Alternatively, workflow2 has problematic result:

* Step 1: Client is online, request access to payment topic
* Step 2: Server fetches the path to payment
* Step 3: Client is free to write to payment DB, without server involvement

As you can see, in step 3, client is free to write to payment db. This is not good. You may be able to argue that it is possible to let client charge by Stripe by itself, and then write to payment if charge success, but since client side code should not be trusted, the security risk is too huge to take. In this **very rare use case**, workflow 1 is a better way to go.

### Security & Authentication

Continue from last best practice, if you choose to use **workflow 1 it is easy to do auth**, since you can check authentication by every writes. Simply use [Firebase admin SDK](https://firebase.google.com/docs/admin/setup), and set [security rules](https://firebase.google.com/docs/database/security/) to deny write to everyone. This makes sure that only your server can write to it. But if you **use workflow 2, not so easy**, since the server sends path to client and client writes, this allows anyone who have the path write to the path. 

This is a major drawback of workflow 2. An interesting detail to point out: for write, firebase-alchemy only push, never set the key by itself, it sets the paths to auto-generated keys that makes the path unguessable for malicious users. But still, it is not good to open write access to everyone. As an example to break this, i can login as a legit user, get the path, and just send the path to my evil friend Eve. Now Eve can write freely to Firebase.

To solve this problem, limit write access only to authenticated users, and use one of the two solutions below:

* Use [firebase drop in authentication solution](https://firebase.google.com/docs/auth/)
* Use [JWT token](https://firebase.google.com/docs/auth/admin/create-custom-tokens)

Both of the solution are good solution. Use firebase drop in auth makes it really sweet on your side, that u do not need to do much coding, and the auth operation is all handled by firebase. Firebase even provides library to [bind with UI directly](https://github.com/firebase/FirebaseUI-Web). But this also means you would be heavily rely on firebase, which have less control or programmatic access to users info. 

Because the firebase drop in auth already have detailed tutorials, we are only going to talk about JWT for firebase here. The main points of JWT is followings:

* Proves the client has JWT is from your server
* Send client access rights to Firebase

A workflow example as follows:

* Client requests access to topic
* Server deals with the request
	* Fetch user access rights, put into JWT payload as additional claims 
	* Send JWT back to client
* Client now can read/write with the JWT depend on the access rights you gives, until token expires
