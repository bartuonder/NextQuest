"""User registration and credential checks."""

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from core.security import hash_password, verify_password
from models import User
from schemas.user import UserCreate


class UserAlreadyExistsError(ValueError):
    """Raised when the username or e-mail is already taken."""


def get_by_username(db: Session, username: str) -> User | None:
    stmt = select(User).where(func.lower(User.username) == username.lower())
    return db.scalars(stmt).first()


def get_by_email(db: Session, email: str) -> User | None:
    stmt = select(User).where(func.lower(User.email) == email.lower())
    return db.scalars(stmt).first()


def register(db: Session, data: UserCreate) -> User:
    if get_by_username(db, data.username):
        raise UserAlreadyExistsError("That username is already taken.")
    if get_by_email(db, str(data.email)):
        raise UserAlreadyExistsError("That e-mail address is already registered.")

    user = User(
        username=data.username,
        email=str(data.email),
        full_name=data.full_name,
        hashed_password=hash_password(data.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def authenticate(db: Session, username: str, password: str) -> User | None:
    """Accept either the username or the e-mail address as the login handle."""
    user = get_by_username(db, username) or get_by_email(db, username)
    if user is None or not verify_password(password, user.hashed_password):
        return None
    return user
