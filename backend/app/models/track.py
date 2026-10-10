"""Track model."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.liked_track import LikedTrack
    from app.models.playlist import PlaylistTrack
    from app.models.user import User


class Track(Base, TimestampMixin):
    __tablename__ = "tracks"

    id: Mapped[int] = mapped_column(primary_key=True)
    # Title/artist are indexed because search filters on them.
    title: Mapped[str] = mapped_column(String(255), index=True)
    artist: Mapped[str] = mapped_column(String(255), index=True)
    album: Mapped[str | None] = mapped_column(String(255), nullable=True)
    duration_seconds: Mapped[int]
    # Paths are relative to settings.upload_dir, so moving the storage root
    # (or switching to object storage) doesn't require rewriting rows.
    file_path: Mapped[str] = mapped_column(String(512))
    cover_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    uploaded_by: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )

    uploader: Mapped[User] = relationship(back_populates="uploaded_tracks")
    playlist_items: Mapped[list[PlaylistTrack]] = relationship(
        back_populates="track", cascade="all, delete-orphan"
    )
    liked_by: Mapped[list[LikedTrack]] = relationship(
        back_populates="track", cascade="all, delete-orphan"
    )
