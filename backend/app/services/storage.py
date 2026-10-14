"""File storage for track uploads.

Every filesystem concern lives behind the ``StorageBackend`` interface so the
app can move from local disk to object storage (e.g. S3) later: implement a new
backend and swap the ``get_storage`` dependency. Routers and models only ever
deal with opaque, storage-relative paths (``audio/<uuid>.mp3``), never absolute
ones or the user's original filename.
"""

from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from pathlib import Path

from fastapi import UploadFile
from mutagen import File as MutagenFile
from mutagen import MutagenError

from app.core.config import settings

# Whitelists are the single source of truth for what we accept.
AUDIO_EXTENSIONS = {".mp3", ".wav", ".ogg", ".flac"}
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}

MAX_AUDIO_BYTES = 25 * 1024 * 1024
MAX_COVER_BYTES = 5 * 1024 * 1024

# Read/write uploads a megabyte at a time so a huge file never lands in memory.
_CHUNK_SIZE = 1024 * 1024


class StorageError(ValueError):
    """Raised when an upload is rejected or can't be stored.

    Routers translate this into a 4xx response with the message as ``detail``.
    """


def _extension(filename: str | None, allowed: set[str]) -> str:
    """Return the lowercased extension of ``filename`` if it's allowed."""
    ext = Path(filename or "").suffix.lower()
    if ext not in allowed:
        allowed_list = ", ".join(sorted(allowed))
        given = ext or (filename or "no filename")
        raise StorageError(f"Unsupported file type '{given}'. Allowed: {allowed_list}")
    return ext


class StorageBackend(ABC):
    """Interface every storage backend must implement."""

    @abstractmethod
    def save(
        self,
        upload: UploadFile,
        *,
        prefix: str,
        allowed_extensions: set[str],
        max_bytes: int,
    ) -> str:
        """Validate, persist and return the storage-relative path.

        Must raise ``StorageError`` for a disallowed type, an empty file, or a
        file larger than ``max_bytes``.
        """

    @abstractmethod
    def delete(self, relative_path: str) -> None:
        """Remove a stored file. Silently ignore files that are already gone."""

    @abstractmethod
    def local_path(self, relative_path: str) -> Path:
        """Return a local filesystem path (used to read audio metadata).

        A remote backend would download the object to a temporary file here.
        """


class LocalStorage(StorageBackend):
    """Stores files under a root directory on local disk."""

    def __init__(self, root: Path | str | None = None) -> None:
        self.root = Path(root) if root is not None else settings.upload_dir
        self.root.mkdir(parents=True, exist_ok=True)

    def save(
        self,
        upload: UploadFile,
        *,
        prefix: str,
        allowed_extensions: set[str],
        max_bytes: int,
    ) -> str:
        # Generate the stored name ourselves: the user's filename is untrusted
        # (path traversal, collisions, weird characters) and is only used to
        # pick the extension after it passes the whitelist.
        ext = _extension(upload.filename, allowed_extensions)
        relative_path = f"{prefix}/{uuid.uuid4().hex}{ext}"
        destination = self.root / relative_path
        destination.parent.mkdir(parents=True, exist_ok=True)

        written = 0
        try:
            with destination.open("wb") as target:
                while chunk := upload.file.read(_CHUNK_SIZE):
                    written += len(chunk)
                    if written > max_bytes:
                        limit = max_bytes // (1024 * 1024)
                        raise StorageError(f"File exceeds the {limit}MB limit")
                    target.write(chunk)
        except StorageError:
            destination.unlink(missing_ok=True)
            raise
        except OSError as exc:
            destination.unlink(missing_ok=True)
            raise StorageError("Could not store the uploaded file") from exc
        finally:
            upload.file.close()

        if written == 0:
            destination.unlink(missing_ok=True)
            raise StorageError("Uploaded file is empty")

        return relative_path

    def delete(self, relative_path: str) -> None:
        try:
            (self.root / relative_path).unlink(missing_ok=True)
        except OSError:
            # Deleting the DB row matters more than cleaning the file; a stale
            # file is harmless and can be reaped later.
            pass

    def local_path(self, relative_path: str) -> Path:
        return self.root / relative_path


def get_storage() -> StorageBackend:
    """FastAPI dependency returning the active storage backend.

    Override this (or replace the body) to switch implementations.
    """
    return LocalStorage()


def read_duration_seconds(relative_path: str, storage: StorageBackend) -> int:
    """Return the audio duration in whole seconds, or 0 if it can't be read.

    A file that passed the extension whitelist can still be corrupt; we don't
    fail the whole upload for that, we just record a duration of 0.
    """
    try:
        audio = MutagenFile(storage.local_path(relative_path))
    except (MutagenError, OSError):
        return 0
    if audio is None or audio.info is None:
        return 0
    return int(round(audio.info.length))


__all__ = [
    "AUDIO_EXTENSIONS",
    "IMAGE_EXTENSIONS",
    "MAX_AUDIO_BYTES",
    "MAX_COVER_BYTES",
    "LocalStorage",
    "StorageBackend",
    "StorageError",
    "get_storage",
    "read_duration_seconds",
]
