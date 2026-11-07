"""Playlist endpoints.

Every playlist identified by id is scoped to its owner: reading, editing,
deleting and reordering all require the authenticated user to own it.
"""

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db import get_db
from app.dependencies import get_current_user
from app.models import Playlist, PlaylistTrack, Track, User
from app.schemas.playlist import (
    PlaylistCreate,
    PlaylistDetail,
    PlaylistOut,
    PlaylistReorder,
    PlaylistTrackAdd,
    PlaylistUpdate,
)

router = APIRouter()


def _owned_playlist(db: Session, playlist_id: int, user: User) -> Playlist:
    """Load a playlist and ensure ``user`` owns it (404 / 403 otherwise)."""
    playlist = db.get(Playlist, playlist_id)
    if playlist is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Playlist not found"
        )
    if playlist.owner_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only access playlists you own",
        )
    return playlist


def _detail(playlist: Playlist) -> PlaylistDetail:
    """Build a detail response from an ORM playlist (tracks in order)."""
    tracks = [item.track for item in playlist.items]
    return PlaylistDetail(
        id=playlist.id,
        name=playlist.name,
        owner_id=playlist.owner_id,
        is_public=playlist.is_public,
        created_at=playlist.created_at,
        track_count=len(tracks),
        tracks=tracks,
    )


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
    name = payload.name.strip()
    if not name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Playlist name cannot be empty",
        )
    playlist = Playlist(
        name=name,
        owner_id=current_user.id,
        is_public=payload.is_public,
    )
    db.add(playlist)
    db.commit()
    db.refresh(playlist)
    return playlist


@router.get("/{playlist_id}", response_model=PlaylistDetail)
def get_playlist(
    playlist_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return one owned playlist with its tracks in order."""
    playlist = _owned_playlist(db, playlist_id, current_user)
    return _detail(playlist)


@router.patch("/{playlist_id}", response_model=PlaylistOut)
def update_playlist(
    playlist_id: int,
    payload: PlaylistUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Rename or change the visibility of an owned playlist."""
    playlist = _owned_playlist(db, playlist_id, current_user)

    if payload.name is not None:
        name = payload.name.strip()
        if not name:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Playlist name cannot be empty",
            )
        playlist.name = name
    if payload.is_public is not None:
        playlist.is_public = payload.is_public

    db.commit()
    db.refresh(playlist)
    return playlist


@router.delete("/{playlist_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_playlist(
    playlist_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    """Delete an owned playlist (and its track associations)."""
    playlist = _owned_playlist(db, playlist_id, current_user)
    db.delete(playlist)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/{playlist_id}/tracks",
    response_model=PlaylistDetail,
    status_code=status.HTTP_201_CREATED,
)
def add_track(
    playlist_id: int,
    payload: PlaylistTrackAdd,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Append a track to an owned playlist."""
    playlist = _owned_playlist(db, playlist_id, current_user)

    track = db.get(Track, payload.track_id)
    if track is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Track not found"
        )

    existing = db.get(PlaylistTrack, (playlist_id, payload.track_id))
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Track is already in this playlist",
        )

    max_position = db.scalar(
        select(func.max(PlaylistTrack.position)).where(
            PlaylistTrack.playlist_id == playlist_id
        )
    )
    position = 0 if max_position is None else max_position + 1

    db.add(
        PlaylistTrack(
            playlist_id=playlist_id,
            track_id=payload.track_id,
            position=position,
        )
    )
    db.commit()
    db.refresh(playlist)
    return _detail(playlist)


@router.delete(
    "/{playlist_id}/tracks/{track_id}", status_code=status.HTTP_204_NO_CONTENT
)
def remove_track(
    playlist_id: int,
    track_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    """Remove a track from an owned playlist and compact positions."""
    playlist = _owned_playlist(db, playlist_id, current_user)

    item = db.get(PlaylistTrack, (playlist_id, track_id))
    if item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Track is not in this playlist",
        )

    db.delete(item)
    db.flush()

    remaining = db.scalars(
        select(PlaylistTrack)
        .where(PlaylistTrack.playlist_id == playlist_id)
        .order_by(PlaylistTrack.position)
    ).all()
    for position, entry in enumerate(remaining):
        entry.position = position

    db.commit()
    db.refresh(playlist)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.put("/{playlist_id}/reorder", response_model=PlaylistDetail)
def reorder_playlist(
    playlist_id: int,
    payload: PlaylistReorder | list[int],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Reorder an owned playlist using a complete ordered list of track ids.

    Accepts either ``{"track_ids": [...]}`` or a bare JSON array of ids.
    """
    playlist = _owned_playlist(db, playlist_id, current_user)

    track_ids = payload if isinstance(payload, list) else payload.track_ids
    if len(track_ids) != len(set(track_ids)):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Track ids must not contain duplicates",
        )

    items = db.scalars(
        select(PlaylistTrack).where(PlaylistTrack.playlist_id == playlist_id)
    ).all()
    current_ids = {item.track_id for item in items}
    if set(track_ids) != current_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Track ids must match the tracks currently in the playlist",
        )

    by_track_id = {item.track_id: item for item in items}
    for position, track_id in enumerate(track_ids):
        by_track_id[track_id].position = position

    db.commit()
    db.refresh(playlist)
    return _detail(playlist)
