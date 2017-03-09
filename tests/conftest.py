# fixtures

import pytest

# sqlalchemy support
from sqlalchemy.orm import sessionmaker
from firebase_alchemy.manager import Adaptor
from sqlalchemy import create_engine

DB_URL = "postgresql://aaron:1@localhost/testing"
FIRE_URL = 'https://casual-local.firebaseio.com/'

@pytest.fixture(scope='session')
def engine(request):
    DATABASE_URL=DB_URL
    engine = create_engine(DATABASE_URL)
    def teardown():
        from _util import drop_db
        drop_db(DATABASE_URL)
    request.addfinalizer(teardown)
    return engine

@pytest.fixture(scope='session')
def _schema(engine):
    """setup test schema, this is only available for other fixtures
    """
    from sqlalchemy.ext.declarative import declarative_base
    from sqlalchemy.orm import relationship
    from sqlalchemy import (
        Column,
        Integer,
        String,
        ForeignKey,
        Table,
        UniqueConstraint,
        create_engine
    )
    from firebase_alchemy.mixin import FireMix
    Base = declarative_base()
    user_chats = Table('chat_map',
                       Base.metadata,
                       Column('index', Integer, primary_key=True),
                       Column('user_fk', Integer, ForeignKey('users.id', ondelete='SET NULL')),
                       Column('chat_fk', Integer, ForeignKey('chats.id', ondelete='SET NULL')))

    class User(Base):
        __tablename__ = 'users'
        id = Column(Integer, primary_key=True)
        name = Column(String, unique=True)
        chats = relationship('Chat',
                             secondary=user_chats,
                             lazy='dynamic')

    class Chat(Base, FireMix):
        __tablename__ = 'chats'
        id = Column(Integer, primary_key=True)
        name = Column(String)
        users = relationship('User',
                             secondary=user_chats,
                             lazy='dynamic')
    # setup
    Base.metadata.create_all(engine)
    return {'user': User, 'chat': Chat}

@pytest.fixture(scope='function')
def session(engine, request):
    """Creates a scoped session for each tests.
    """
    from sqlalchemy.orm import scoped_session
    from sqlalchemy.orm import sessionmaker

    session_factory = sessionmaker(bind=engine)
    Session = scoped_session(session_factory)

    def teardown():
        Session.remove()

    request.addfinalizer(teardown)
    return Session()

@pytest.fixture(scope='function')
def adaptor(session):
    """return an adaptor relative to a scope session.
    """
    return Adaptor(session,
                   fire_url=FIRE_URL)

@pytest.fixture(scope='function')
def user_model(_schema, session):
    """return a user table and clean up after myself
    """
    table = _schema['user']
    yield table
    session.query(table).delete()
    session.commit()

@pytest.fixture(scope='function')
def chat_model(_schema, session):
    """return a user table and clean up after myself
    """
    table = _schema['chat']
    yield table
    session.query(table).delete()
    session.commit()

@pytest.fixture(scope='session')
def firebase_inspector():
    """a independent inspector that clean after itself
    """
    from firebase import FirebaseApplication
    client = FirebaseApplication(FIRE_URL)
    yield client
    print '---- firebase cleanup ----'
    client.delete('test', None)
    print '-- firebase cleanup end --'

@pytest.fixture(scope='module')
def fire_url():
    """return fireurl for path testing
    """
    return FIRE_URL