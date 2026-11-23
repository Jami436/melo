"""Pydantic schemas for the search endpoint."""

from pydantic import BaseModel, ConfigDict

from app.schemas.track import TrackOut, TrackPage


class ArtistHit(BaseModel):
    """An artist group built from the tracks that matched the query."""

    model_config = ConfigDict(from_attributes=True)

    name: str
    track_count: int
    top_track: TrackOut


class ArtistPage(BaseModel):
    """One page of artist groups."""

    items: list[ArtistHit]
    total: int
    page: int
    size: int


class SearchResponse(BaseModel):
    """Tracks and artists matching a query, each paginated."""

    query: str
    tracks: TrackPage
    artists: ArtistPage
