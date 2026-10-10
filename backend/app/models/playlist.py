"""Playlist and its association object with tracks."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String, func, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.track import Track
    from app.models.user import User


class Playlist(Base, TimestampMixin):
    __tablename__ = "playlists"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    owner_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    # Public playlists can be shared/listed; private ones only show for the owner.
    is_public: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default=text("true")
    )

    owner: Mapped[User] = relationship(back_populates="playlists")
    items: Mapped[list[PlaylistTrack]] = relationship(
        back_populates="playlist",
        cascade="all, delete-orphan",
        order_by="PlaylistTrack.position",
    )


class PlaylistTrack(Base):
    """Association object: one track's place inside one playlist.

    Modelled as a full class (rather than a plain ``secondary`` table) because
    the relationship carries extra data: ``position`` and ``added_at``.
    The composite primary key ``(playlist_id, track_id)`` prevents adding the
    same track twice, while ``position`` stores explicit ordering.
    """

    __tablename__ = "playlist_tracks"
    __table_args__ = (
        # Speeds up "give me this playlist already sorted".
        Index("ix_playlist_tracks_playlist_position", "playlist_id", "position"),
    )

    playlist_id: Mapped[int] = mapped_column(
        ForeignKey("playlists.id", ondelete="CASCADE"), primary_key=True
    )
    track_id: Mapped[int] = mapped_column(
        ForeignKey("tracks.id", ondelete="CASCADE"), primary_key=True
    )
    position: Mapped[int]
    added_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    playlist: Mapped[Playlist] = relationship(back_populates="items")
    track: Mapped[Track] = relationship(back_populates="playlist_items")
