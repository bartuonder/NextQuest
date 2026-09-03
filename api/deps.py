from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from core.database import get_db
from core.security import decode_access_token
from models import User
from services.llm_engine import RecommendationEngine, get_engine

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/token")

DbSession = Annotated[Session, Depends(get_db)]


def get_current_user(
    db: DbSession, token: Annotated[str, Depends(oauth2_scheme)]
) -> User:
    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials.",
        headers={"WWW-Authenticate": "Bearer"},
    )

    subject = decode_access_token(token)
    if subject is None or not subject.isdigit():
        raise credentials_error

    user = db.get(User, int(subject))
    if user is None:
        raise credentials_error
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]
Engine = Annotated[RecommendationEngine, Depends(get_engine)]
