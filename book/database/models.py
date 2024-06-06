from sqlalchemy import Column, Integer, String, ForeignKey, BIGINT
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship


Base = declarative_base()


class User(Base):
    __tablename__ = 'users'
    user_id = Column(BIGINT, primary_key=True)
    username = Column(String)
    first_name = Column(String)
    last_name = Column(String, nullable=True)
    bookmarks = relationship('BookMark', back_populates='user')


class Book(Base):
    __tablename__ = 'books'
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, unique=True, index=True)
    bookmarks = relationship("BookMark", back_populates="books")
    book_page = relationship("BookPage", back_populates="book_pages")

    def __repr__(self):
        return f"{self.name}"


class BookMark(Base):
    __tablename__ = 'bookmarks'
    bookmark_id = Column(Integer, primary_key=True, autoincrement=True)
    text = Column(String)
    user_id = Column(BIGINT, ForeignKey('users.user_id', ondelete='CASCADE'), nullable=False)
    book_id = Column(Integer, ForeignKey('books.id', ondelete='CASCADE'), nullable=False)
    book_page = Column(Integer, ForeignKey('book_page.id', ondelete='CASCADE'), nullable=False)
    user = relationship('User', back_populates='bookmarks')
    books = relationship('Book', back_populates='bookmarks')


class BookPage(Base):
    __tablename__ = "book_page"
    id = Column(Integer, primary_key=True, autoincrement=True, index=True)
    text = Column(String)
    book_id = Column(Integer, ForeignKey('books.id'), nullable=False)
    book_pages = relationship('Book', back_populates='book_page')
