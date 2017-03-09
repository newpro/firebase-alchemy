"""This is an example of usage.

In this example, we are building a data structure of user and chats,
and efficiently create chats, queue chat(s), and push info into chats.
"""
# sqlalchemy
from os import environ
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy import Column, Integer, String, ForeignKey, Table, UniqueConstraint, create_engine
# native
from firebase_alchemy.mixin import FireMix
from firebase_alchemy.manager import Adaptor, ModelManager

# fetch test environment
try:
    DB_URL = environ['DB_URL'] # sqlalchemy db url
    FIRE_URL = environ['FIRE_URL'] # the path to your firebase project
except:
    # fill yours in here
    DB_URL = 'postgresql://[username]:[password]@[location]/[db_name]'
    FIRE_URL = 'https://[project_name].firebaseio.com'

print "---", DB_URL
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
