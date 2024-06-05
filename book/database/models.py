from sqlalchemy import Column, Integer, String, ForeignKey, BIGINT
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()


class Book(Base):
    __tablename__ = 'books'
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String)
    author = Column(String)
    text = Column(String)

    def __repr__(self):
        return f"Книга {self.name}"


class User(Base):
    __tablename__ = 'users'
    user_id = Column(BIGINT, primary_key=True)
    username = Column(String)
    first_name = Column(String)
    last_name = Column(String, nullable=True)
    bookmarks = relationship('BookMark', back_populates='user')


class BookMark(Base):
    __tablename__ = 'bookmarks'
    bookmark_id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(BIGINT, ForeignKey('users.user_id', ondelete='CASCADE'), nullable=False)
    user = relationship('User', back_populates='bookmarks')
    text = Column(String)
