"""User model."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:  # avoid runtime import cycles; names resolved lazily below
    from app.models.liked_track import LikedTrack
    from app.models.playlist import Playlist
    from app.models.track import Track


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    # Unique + indexed: the identity columns we look users up by.
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255))

    # Deleting a user cleans up everything they own (ORM-level cascade;
    # the FKs also declare ondelete="CASCADE" for database-level safety).
    uploaded_tracks: Mapped[list[Track]] = relationship(
        back_populates="uploader", cascade="all, delete-orphan"
    )
    playlists: Mapped[list[Playlist]] = relationship(
        back_populates="owner", cascade="all, delete-orphan"
    )
    liked_tracks: Mapped[list[LikedTrack]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
