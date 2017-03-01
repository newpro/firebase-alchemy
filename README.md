# firebase-alchemy
Firebase backed by sqlalchemy for faster query processing

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

Continue as the example, since the system is build on SQL, it can effectively fetch info from server side and send it to one listening client. 

In this example, Let us say Bill is a client, and he is online to chat. The server can get all bills chat in SQL fashion: 

```python
bill.chats
```

And when bill click on chat2 and start to chat, the server simply tells the client what it should listen to, by fetch the path of chat2 in Firebase. You can use our old friend ChatManager to get the fire:

```python
chat_manager.get_path(chat2)
```

Then the server can send this path to client to listen to. Client can perform various firebase operations as before.
