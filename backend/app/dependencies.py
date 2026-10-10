"""Shared FastAPI dependencies.

``get_current_user`` lives here (not in a router) so any future router can
require an authenticated user without duplicating token handling.
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.security import JWTError, decode_access_token
from app.db import get_db
from app.models import User

# auto_error=False lets us raise our own consistent 401 (with the
# WWW-Authenticate header) instead of Starlette's default 403 for a missing
# Authorization header.
bearer_scheme = HTTPBearer(auto_error=False)


def _unauthorized() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    """Resolve the authenticated user from the Bearer token, or raise 401."""
    if credentials is None:
        raise _unauthorized()

    try:
        payload = decode_access_token(credentials.credentials)
        user_id = int(payload["sub"])
    except (JWTError, KeyError, TypeError, ValueError):
        # Covers bad signature, expired token, malformed payload, non-numeric sub.
        raise _unauthorized()

    user = db.get(User, user_id)
    if user is None:
        # Token was valid but the user no longer exists.
        raise _unauthorized()
    return user
