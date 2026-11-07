"""Current-user endpoints (liked songs)."""

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.dependencies import get_current_user
from app.models import LikedTrack, Track, User
from app.schemas.track import TrackOut

router = APIRouter()


@router.get("/likes", response_model=list[TrackOut])
def list_liked_tracks(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return the authenticated user's liked tracks, newest first."""
    tracks = db.scalars(
        select(Track)
        .join(LikedTrack, LikedTrack.track_id == Track.id)
        .where(LikedTrack.user_id == current_user.id)
        .order_by(LikedTrack.created_at.desc(), Track.id.desc())
    ).all()
    return list(tracks)
