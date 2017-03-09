"""Sqlalchemy mixin
"""

from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy import Column, String

class FireMix():
    """
    Base declaratived
    """
    @declared_attr
    def __firepath__(cls):
        return cls.__name__.lower() # use db class as firepath

    fireid = Column(String, unique=True, nullable=True, index=True)
