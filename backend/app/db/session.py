"""Database engine, session factory and the FastAPI session dependency."""

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings

# One engine (connection pool) per process. pool_pre_ping quietly drops stale
# connections, which is common with long-lived dev servers.
engine = create_engine(settings.database_url, pool_pre_ping=True)

# autoflush=False: avoid surprise flushes mid-request; we commit explicitly.
# expire_on_commit=False: keep ORM objects usable after commit() so response
# serialization doesn't trigger extra queries.
SessionLocal = sessionmaker(
    bind=engine, autoflush=False, autocommit=False, expire_on_commit=False
)


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency: yields a session and always closes it."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
