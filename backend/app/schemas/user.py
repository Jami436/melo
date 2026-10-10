"""Pydantic schemas for users and auth tokens.

``UserOut`` deliberately has no password/auth fields so a hashed password can
never leak through a response.
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserCreate(BaseModel):
    """Signup payload."""

    email: EmailStr
    username: str = Field(min_length=3, max_length=50)
    password: str = Field(min_length=8, max_length=128)


class UserLogin(BaseModel):
    """Login payload (email + password)."""

    email: EmailStr
    password: str


class UserOut(BaseModel):
    """Public representation of a user. Never includes secrets."""

    # from_attributes lets us return an ORM ``User`` directly.
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    username: str
    created_at: datetime


class Token(BaseModel):
    """Bearer token returned by /auth/login."""

    access_token: str
    token_type: str = "bearer"
