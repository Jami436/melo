"""Search router."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db import get_db
from app.schemas.search import SearchResponse
from app.services.search import search

router = APIRouter()


@router.get("", response_model=SearchResponse)
def search_tracks(
    db: Session = Depends(get_db),
    q: str = Query("", max_length=200),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
) -> SearchResponse:
    """Return tracks and artists matching q, ranked by relevance."""
    return search(db, q, page, size)
