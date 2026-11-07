"""Pydantic schemas for playlists."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.track import TrackOut


class PlaylistCreate(BaseModel):
    """Payload for creating a playlist."""

    name: str = Field(min_length=1, max_length=255)
    is_public: bool = True


class PlaylistUpdate(BaseModel):
    """Payload for renaming a playlist or changing its visibility."""

    name: str | None = Field(default=None, min_length=1, max_length=255)
    is_public: bool | None = None


class PlaylistTrackAdd(BaseModel):
    """Payload for adding a track to a playlist."""

    track_id: int


class PlaylistReorder(BaseModel):
    """Ordered list of every track id currently in the playlist."""

    track_ids: list[int]


class PlaylistOut(BaseModel):
    """Public representation of a playlist summary."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    owner_id: int
    is_public: bool
    created_at: datetime
    track_count: int


class PlaylistDetail(PlaylistOut):
    """A playlist plus its tracks, already in playlist order."""

    tracks: list[TrackOut]
