"""Password hashing and JWT helpers.

Kept free of database/request concerns: routers and the ``get_current_user``
dependency compose these primitives.
"""

from datetime import datetime, timedelta, timezone
from typing import Any

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings

# bcrypt is intentionally the only scheme; ``deprecated="auto"`` lets existing
# hashes be upgraded transparently if we ever add another scheme.
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """Return a salted bcrypt hash (never store the plain password)."""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Constant-time check of a plain password against a stored hash."""
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(
    subject: str | int, expires_minutes: int | None = None
) -> str:
    """Create a signed JWT whose ``sub`` is the user id.

    ``exp`` makes the token expire; ``iat`` records when it was issued.
    """
    now = datetime.now(timezone.utc)
    expire = now + timedelta(
        minutes=expires_minutes
        if expires_minutes is not None
        else settings.access_token_expire_minutes
    )
    payload = {"sub": str(subject), "iat": now, "exp": expire}
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict[str, Any]:
    """Decode and validate a token.

    Raises ``jose.JWTError`` for a bad signature, malformed token, or expired
    token — callers translate that into a 401.
    """
    return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])


__all__ = [
    "hash_password",
    "verify_password",
    "create_access_token",
    "decode_access_token",
    "JWTError",
]
