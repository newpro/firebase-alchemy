"""This is an example of usage.

In this example, we are building a data structure of user and chats,
and efficiently create chats, queue chat(s), and push info into chats.
"""
# sqlalchemy
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy import Column, Integer, String, ForeignKey, Table, UniqueConstraint, create_engine
# native
from firebase_alchemy.mixin import FireMix
from firebase_alchemy.manager import Adaptor, ModelManager

# fetch test environment
try:
    DB_URL = os.environ['DB_URL'] # sqlalchemy db url
    FIRE_URL = os.environ['FIRE_URL'] # the path to yours 
except:
    DB_URL = 'postgresql://[username]:[password]@[location]/[db_name]'
    FIRE_URL = 'https://[project_name].firebaseio.com'

# build relational parts
engine = create_engine(DB_URL)
Base = declarative_base()
Session = sessionmaker(bind=engine)
session = Session()

# many to many table
user_chats = Table('chat_map',
                   Base.metadata,
                   Column('index', Integer, primary_key=True),
                   Column('user_fk', Integer, ForeignKey('users.id')),
                   Column('chat_fk', Integer, ForeignKey('chats.id'))
                   )

# User is a normal sqlalchmy class since do not need to store in firebase
class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True)
    chats = relationship('Chat',
                         secondary=user_chats,
                         lazy='dynamic')

# Chat is a mixed class
class Chat(Base, FireMix):
    __tablename__ = 'chats'
    id = Column(Integer, primary_key=True)
    name = Column(String)
    users = relationship('User',
                         secondary=user_chats,
                         lazy='dynamic')

Base.metadata.create_all(engine)

# !!! Link managers !!!
adaptor = Adaptor(session, FIRE_URL)
# for each model class that link to firebase, bind a manager
chat_manager = ModelManager(adaptor, Chat, firepath='chats', validator=['msg', 'who'])

# users
aaron = User(name='aaron')
bill = User(name='bill')
colin = User(name='colin')
session.add_all([aaron, bill, colin])
session.commit()

# chats
chat1 = chat_manager.add(name='Sunday Picnic')
chat2 = chat_manager.add(name='Colin surprise birthday party')

# some relationships
chat1.users.append(aaron)
chat1.users.append(colin)
chat2.users.append(aaron)
chat2.users.append(bill)
session.commit()

# fetch queue as fast and easy as sqlalchemy!
print '{} in chat for {}: {} '.format(colin.name, chat1.name, colin in chat1.users)
print '{} in chat for {}: {} '.format(colin.name, chat2.name, colin in chat2.users)

# chat about something
chat_manager.push(chat2, {'msg': 'Let us throw colin a suprise party!',
                          'who': aaron.name})
chat_manager.push(chat2, {'msg': 'Yeah agree!',
                          'who': bill.name})

# delete the instance in db and firebase
#chat_manager.delete(chat2) # uncomment this to remove chat
