"""Pydantic schemas for playlists."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class PlaylistCreate(BaseModel):
    """Payload for creating a playlist."""

    name: str = Field(min_length=1, max_length=255)
    is_public: bool = True


class PlaylistOut(BaseModel):
    """Public representation of a playlist."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    owner_id: int
    is_public: bool
    created_at: datetime
