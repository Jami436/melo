"""LikedTrack association model (users <-> tracks)."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.track import Track
    from app.models.user import User


class LikedTrack(Base):
    """Many-to-many "a user likes a track".

    The composite primary key ``(user_id, track_id)`` makes liking idempotent
    (you can't like the same track twice), while ``created_at`` lets the UI sort
    liked songs by when they were saved.
    """

    __tablename__ = "liked_tracks"

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    track_id: Mapped[int] = mapped_column(
        ForeignKey("tracks.id", ondelete="CASCADE"), primary_key=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    user: Mapped[User] = relationship(back_populates="liked_tracks")
    track: Mapped[Track] = relationship(back_populates="liked_by")
