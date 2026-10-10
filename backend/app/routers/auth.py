"""Authentication endpoints: signup, login and current-user lookup."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.security import create_access_token, hash_password, verify_password
from app.db import get_db
from app.dependencies import get_current_user
from app.models import User
from app.schemas.user import Token, UserCreate, UserLogin, UserOut

router = APIRouter()


@router.post("/signup", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def signup(payload: UserCreate, db: Session = Depends(get_db)) -> User:
    """Register a new user, rejecting duplicate email or username."""
    # Check each identifier separately so the error names the actual conflict.
    if db.scalar(select(User).where(User.email == payload.email)):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email is already registered",
        )
    if db.scalar(select(User).where(User.username == payload.username)):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username is already taken",
        )

    user = User(
        email=payload.email,
        username=payload.username,
        hashed_password=hash_password(payload.password),
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        # Safety net for a race between the checks above and the commit;
        # the unique constraints are the real source of truth.
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email or username already exists",
        )
    db.refresh(user)
    return user


@router.post("/login", response_model=Token)
def login(payload: UserLogin, db: Session = Depends(get_db)) -> Token:
    """Verify credentials and return a JWT access token."""
    user = db.scalar(select(User).where(User.email == payload.email))

    # Same error whether the email is unknown or the password is wrong, so we
    # don't reveal which accounts exist.
    if user is None or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return Token(access_token=create_access_token(user.id))


@router.get("/me", response_model=UserOut)
def read_me(current_user: User = Depends(get_current_user)) -> User:
    """Return the authenticated user."""
    return current_user
