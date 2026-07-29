from core.database import Base
from sqlalchemy import Column, String, Integer, ForeignKey


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    first_name = Column(String)
    middle_name = Column(String, nullable=True)
    last_name = Column(String)


class Movie(Base):
    __tablename__ = "movies"

    id = Column(Integer, primary_key=True, index=True)
    first_movie = Column(String)
    second_movie = Column(String, nullable=True)
    third_movie = Column(String, nullable=True)
    owner = Column(Integer, ForeignKey("users.id"))


class Game(Base):
    __tablename__ = "games"

    id = Column(Integer, primary_key=True, index=True)
    first_game = Column(String)
    second_game = Column(String, nullable=True)
    third_game = Column(String, nullable=True)
    owner = Column(Integer, ForeignKey("users.id"))


class TVSeries(Base):
    __tablename__ = "tv_series"

    id = Column(Integer, primary_key=True, index=True)
    first_serie = Column(String)
    second_serie = Column(String, nullable=True)
    third_serie = Column(String, nullable=True)
    owner = Column(Integer, ForeignKey("users.id"))


class Anime(Base):
    __tablename__ = "animes"

    id = Column(Integer, primary_key=True, index=True)
    first_anime = Column(String)
    second_anime = Column(String, nullable=True)
    third_anime = Column(String, nullable=True)
    owner = Column(Integer, ForeignKey("users.id"))


class Book(Base):
    __tablename__ = "books"

    id = Column(Integer, primary_key=True, index=True)
    first_book = Column(String)
    second_book = Column(String, nullable=True)
    third_book = Column(String, nullable=True)
    owner = Column(Integer, ForeignKey("users.id"))