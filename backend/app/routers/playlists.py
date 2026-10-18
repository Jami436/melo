"""Playlist endpoints: list and create."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.dependencies import get_current_user
from app.models import Playlist, User
from app.schemas.playlist import PlaylistCreate, PlaylistOut

router = APIRouter()


@router.get("", response_model=list[PlaylistOut])
def list_playlists(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return the authenticated user's playlists."""
    playlists = (
        db.query(Playlist)
        .filter(Playlist.owner_id == current_user.id)
        .order_by(Playlist.created_at.desc())
        .all()
    )
    return playlists


@router.post("", response_model=PlaylistOut, status_code=status.HTTP_201_CREATED)
def create_playlist(
    payload: PlaylistCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new playlist owned by the authenticated user."""
    playlist = Playlist(
        name=payload.name.strip(),
        owner_id=current_user.id,
        is_public=payload.is_public,
    )
    db.add(playlist)
    db.commit()
    db.refresh(playlist)
    return playlist
