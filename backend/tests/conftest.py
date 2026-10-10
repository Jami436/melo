"""Pytest fixtures.

Tests run against a throwaway in-memory SQLite database instead of PostgreSQL:
the ``get_db`` dependency is overridden, so the suite is self-contained and
never touches a real database.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401  (registers tables on Base.metadata)
from app.db import get_db
from app.db.base import Base
from app.main import app

# One shared in-memory database for the whole test session.
# StaticPool + check_same_thread=False keep the same connection alive across
# requests so the schema we create is visible everywhere.
engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(
    bind=engine, autoflush=False, autocommit=False, expire_on_commit=False
)


def _override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


# Every request that needs a session gets the test session instead.
app.dependency_overrides[get_db] = _override_get_db


@pytest.fixture(autouse=True)
def _fresh_schema():
    """Give each test a clean schema."""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client
