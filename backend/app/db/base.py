"""SQLAlchemy declarative base and shared column mixins."""

from datetime import datetime

from sqlalchemy import DateTime, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Base class every ORM model inherits from.

    SQLAlchemy registers all mapped subclasses on ``Base.metadata``; Alembic's
    autogenerate compares that metadata against the live database.
    """


class TimestampMixin:
    """Adds a ``created_at`` column filled in by the database on insert.

    Using ``server_default=func.now()`` (instead of a Python default) means the
    timestamp comes from PostgreSQL, so rows inserted outside the ORM also get
    a consistent value.
    """

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
