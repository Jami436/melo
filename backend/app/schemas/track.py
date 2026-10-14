"""Pydantic schemas for track endpoints.

``TrackOut`` mirrors the public shape of a ``Track`` ORM row. File paths are
returned as storage-relative strings (e.g. ``audio/ab12....mp3``); a client
resolves them against the storage root rather than receiving an absolute path.
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class TrackOut(BaseModel):
    """Public representation of a track."""

    # from_attributes lets us return an ORM ``Track`` directly.
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    artist: str
    album: str | None
    duration_seconds: int
    file_path: str
    cover_path: str | None
    uploaded_by: int
    created_at: datetime


class TrackPage(BaseModel):
    """One page of tracks plus the total count for pagination."""

    items: list[TrackOut]
    total: int
    page: int
    size: int
