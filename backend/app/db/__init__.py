"""Database package.

Re-exports ``Base``/``TimestampMixin`` eagerly (importing a model must not
create a DB connection), and exposes ``engine``/``SessionLocal``/``get_db``
lazily via PEP 562 so ``from app.db import get_db`` still works in routers.
"""

from app.db.base import Base, TimestampMixin

_LAZY = {"engine", "SessionLocal", "get_db"}

__all__ = ["Base", "TimestampMixin", "engine", "SessionLocal", "get_db"]


def __getattr__(name: str):
    if name in _LAZY:
        from app.db import session

        return getattr(session, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
