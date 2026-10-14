"""Track endpoints: upload, list, fetch and delete.

All storage work is delegated to ``app.services.storage``; this module only
handles HTTP concerns (validation of form fields, auth, status codes).
"""

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    Response,
    UploadFile,
    status,
)
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db import get_db
from app.dependencies import get_current_user
from app.models import Track, User
from app.schemas.track import TrackOut, TrackPage
from app.services.storage import (
    AUDIO_EXTENSIONS,
    IMAGE_EXTENSIONS,
    MAX_AUDIO_BYTES,
    MAX_COVER_BYTES,
    StorageBackend,
    StorageError,
    get_storage,
    read_duration_seconds,
)

router = APIRouter()


def _reject(exc: StorageError) -> HTTPException:
    # 400 keeps "file too large" and "bad file type" in one predictable place.
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.post("/upload", response_model=TrackOut, status_code=status.HTTP_201_CREATED)
def upload_track(
    file: UploadFile = File(..., description="Audio file (mp3, wav, ogg, flac)"),
    title: str = Form(..., min_length=1, max_length=255),
    artist: str = Form(..., min_length=1, max_length=255),
    album: str | None = Form(None, max_length=255),
    cover: UploadFile | None = File(None, description="Optional cover image"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    storage: StorageBackend = Depends(get_storage),
) -> Track:
    """Store an audio file (+ optional cover) and record it as a track."""
    try:
        file_path = storage.save(
            file,
            prefix="audio",
            allowed_extensions=AUDIO_EXTENSIONS,
            max_bytes=MAX_AUDIO_BYTES,
        )
    except StorageError as exc:
        raise _reject(exc)

    cover_path: str | None = None
    if cover is not None:
        try:
            cover_path = storage.save(
                cover,
                prefix="covers",
                allowed_extensions=IMAGE_EXTENSIONS,
                max_bytes=MAX_COVER_BYTES,
            )
        except StorageError as exc:
            # Don't leave the audio file behind if the cover is rejected.
            storage.delete(file_path)
            raise _reject(exc)

    track = Track(
        title=title.strip(),
        artist=artist.strip(),
        album=album.strip() if album and album.strip() else None,
        duration_seconds=read_duration_seconds(file_path, storage),
        file_path=file_path,
        cover_path=cover_path,
        uploaded_by=current_user.id,
    )
    db.add(track)
    try:
        db.commit()
    except Exception:
        # Roll back the DB *and* the files so nothing is half-created.
        db.rollback()
        storage.delete(file_path)
        if cover_path is not None:
            storage.delete(cover_path)
        raise
    db.refresh(track)
    return track


@router.get("", response_model=TrackPage)
def list_tracks(
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
) -> TrackPage:
    """Return a page of tracks, newest first."""
    total = db.scalar(select(func.count()).select_from(Track)) or 0
    rows = db.scalars(
        select(Track)
        .order_by(Track.created_at.desc(), Track.id.desc())
        .offset((page - 1) * size)
        .limit(size)
    ).all()
    return TrackPage(items=list(rows), total=total, page=page, size=size)


@router.get("/{track_id}", response_model=TrackOut)
def get_track(track_id: int, db: Session = Depends(get_db)) -> Track:
    """Return a single track by id."""
    track = db.get(Track, track_id)
    if track is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Track not found"
        )
    return track


@router.delete("/{track_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_track(
    track_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    storage: StorageBackend = Depends(get_storage),
) -> Response:
    """Delete a track. Only the user who uploaded it may do so."""
    track = db.get(Track, track_id)
    if track is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Track not found"
        )
    if track.uploaded_by != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only delete tracks you uploaded",
        )

    file_path = track.file_path
    cover_path = track.cover_path
    db.delete(track)
    db.commit()

    # Remove the stored files after the row is gone; the DB is the source of
    # truth and a leftover file can always be reaped later.
    storage.delete(file_path)
    if cover_path is not None:
        storage.delete(cover_path)

    return Response(status_code=status.HTTP_204_NO_CONTENT)
