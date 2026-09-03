from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm

from api.deps import CurrentUser, DbSession
from core.security import create_access_token
from schemas.user import Token, UserCreate, UserLogin, UserRead
from services import auth as auth_service

router = APIRouter(prefix="/auth", tags=["auth"])

INVALID_CREDENTIALS = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Incorrect username or password.",
    headers={"WWW-Authenticate": "Bearer"},
)


def _issue_token(user) -> Token:
    return Token(
        access_token=create_access_token(str(user.id)),
        user=UserRead.model_validate(user),
    )


@router.post("/register", response_model=Token, status_code=status.HTTP_201_CREATED)
def register(db: DbSession, data: UserCreate) -> Token:
    try:
        user = auth_service.register(db, data)
    except auth_service.UserAlreadyExistsError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from exc
    return _issue_token(user)


@router.post("/token", response_model=Token)
def token(
    db: DbSession, form: Annotated[OAuth2PasswordRequestForm, Depends()]
) -> Token:
    """OAuth2 password flow, used by Swagger UI's Authorize button."""
    user = auth_service.authenticate(db, form.username, form.password)
    if user is None:
        raise INVALID_CREDENTIALS
    return _issue_token(user)


@router.post("/login", response_model=Token)
def login(db: DbSession, data: UserLogin) -> Token:
    """JSON login for the web client."""
    user = auth_service.authenticate(db, data.username, data.password)
    if user is None:
        raise INVALID_CREDENTIALS
    return _issue_token(user)


@router.get("/me", response_model=UserRead)
def me(user: CurrentUser) -> UserRead:
    return UserRead.model_validate(user)
