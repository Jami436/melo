"""Tests for the /tracks endpoints."""

import io
import wave

import pytest

from app.main import app
from app.services.streaming import RangeError, parse_range
from app.services.storage import LocalStorage, get_storage


def make_wav_bytes(seconds: int = 1, framerate: int = 8000) -> bytes:
    """Build a valid, silent WAV file in memory so mutagen can read a duration."""
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as writer:
        writer.setnchannels(1)
        writer.setsampwidth(2)
        writer.setframerate(framerate)
        writer.writeframes(b"\x00\x00" * int(framerate * seconds))
    return buffer.getvalue()


def auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def register_and_token(
    client, email: str = "alice@example.com", username: str = "alice"
) -> str:
    signup = client.post(
        "/auth/signup",
        json={"email": email, "username": username, "password": "supersecret"},
    )
    assert signup.status_code == 201, signup.text
    login = client.post(
        "/auth/login", json={"email": email, "password": "supersecret"}
    )
    return login.json()["access_token"]


@pytest.fixture
def storage(tmp_path):
    """Point the app at a throwaway directory instead of backend/uploads."""
    backend = LocalStorage(tmp_path)
    app.dependency_overrides[get_storage] = lambda: backend
    yield backend
    app.dependency_overrides.pop(get_storage, None)


def upload(client, token, *, filename="song.wav", content=None, content_type="audio/wav", **fields):
    data = {"title": "Song", "artist": "Artist"}
    data.update({key: value for key, value in fields.items() if value is not None})
    payload = content if content is not None else make_wav_bytes()
    files = {"file": (filename, payload, content_type)}
    return client.post("/tracks/upload", data=data, files=files, headers=auth(token))


# ---------------------------------------------------------------- upload ----


def test_upload_stores_metadata_and_duration(client, storage):
    token = register_and_token(client)
    response = upload(client, token, album="Album")

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["title"] == "Song"
    assert body["artist"] == "Artist"
    assert body["album"] == "Album"
    assert body["duration_seconds"] == 1
    assert body["uploaded_by"] == 1
    # Stored under a generated UUID name, never the user's filename.
    assert body["file_path"].startswith("audio/")
    assert body["file_path"].endswith(".wav")
    assert "song.wav" not in body["file_path"]
    assert storage.local_path(body["file_path"]).exists()


def test_upload_with_cover(client, storage):
    token = register_and_token(client)
    png = b"\x89PNG\r\n\x1a\n" + b"\x00" * 32
    files = {
        "file": ("song.wav", make_wav_bytes(), "audio/wav"),
        "cover": ("art.png", png, "image/png"),
    }
    response = client.post(
        "/tracks/upload",
        data={"title": "Song", "artist": "Artist"},
        files=files,
        headers=auth(token),
    )

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["cover_path"].startswith("covers/")
    assert storage.local_path(body["cover_path"]).exists()


def test_upload_requires_authentication(client, storage):
    files = {"file": ("song.wav", make_wav_bytes(), "audio/wav")}
    response = client.post(
        "/tracks/upload", data={"title": "Song", "artist": "Artist"}, files=files
    )

    assert response.status_code == 401


# --------------------------------------------------------------- rejects ----


def test_upload_rejects_invalid_file_type(client, storage):
    token = register_and_token(client)
    response = upload(
        client,
        token,
        filename="malware.exe",
        content=b"MZ\x90\x00",
        content_type="application/octet-stream",
    )

    assert response.status_code == 400
    assert "unsupported file type" in response.json()["detail"].lower()
    # Nothing must be written for a rejected upload.
    assert list(storage.root.rglob("*.*")) == []


def test_upload_rejects_oversized_file(client, storage):
    token = register_and_token(client)
    too_big = b"\x00" * (25 * 1024 * 1024 + 1)
    response = upload(
        client, token, filename="big.mp3", content=too_big, content_type="audio/mpeg"
    )

    assert response.status_code == 400
    assert "limit" in response.json()["detail"].lower()
    assert list(storage.root.rglob("*.*")) == []


def test_upload_rejects_bad_cover_type_and_cleans_up_audio(client, storage):
    token = register_and_token(client)
    files = {
        "file": ("song.wav", make_wav_bytes(), "audio/wav"),
        "cover": ("notes.txt", b"not an image", "text/plain"),
    }
    response = client.post(
        "/tracks/upload",
        data={"title": "Song", "artist": "Artist"},
        files=files,
        headers=auth(token),
    )

    assert response.status_code == 400
    # The already-saved audio file must be rolled back too.
    assert list(storage.root.rglob("*.*")) == []


# ------------------------------------------------------------------ list ----


def test_list_tracks_is_paginated(client, storage):
    token = register_and_token(client)
    for index in range(3):
        assert upload(client, token, title=f"Song {index}").status_code == 201

    first = client.get("/tracks", params={"page": 1, "size": 2}).json()
    second = client.get("/tracks", params={"page": 2, "size": 2}).json()

    assert first["total"] == 3
    assert first["page"] == 1
    assert first["size"] == 2
    assert len(first["items"]) == 2
    assert len(second["items"]) == 1


def test_get_track_by_id(client, storage):
    token = register_and_token(client)
    track_id = upload(client, token).json()["id"]

    response = client.get(f"/tracks/{track_id}")

    assert response.status_code == 200
    assert response.json()["id"] == track_id


def test_get_missing_track_is_not_found(client, storage):
    assert client.get("/tracks/999").status_code == 404


# ---------------------------------------------------------------- delete ----


def test_delete_by_non_owner_is_forbidden(client, storage):
    owner = register_and_token(client, email="owner@example.com", username="owner")
    track = upload(client, owner).json()
    other = register_and_token(client, email="other@example.com", username="other")

    response = client.delete(f"/tracks/{track['id']}", headers=auth(other))

    assert response.status_code == 403
    # The track and its file must survive a forbidden delete.
    assert storage.local_path(track["file_path"]).exists()
    assert client.get(f"/tracks/{track['id']}").status_code == 200


def test_delete_requires_authentication(client, storage):
    token = register_and_token(client)
    track = upload(client, token).json()

    assert client.delete(f"/tracks/{track['id']}").status_code == 401


def test_owner_delete_removes_row_and_file(client, storage):
    token = register_and_token(client)
    track = upload(client, token).json()
    path = storage.local_path(track["file_path"])
    assert path.exists()

    response = client.delete(f"/tracks/{track['id']}", headers=auth(token))

    assert response.status_code == 204
    assert not path.exists()
    assert client.get(f"/tracks/{track['id']}").status_code == 404


# --------------------------------------------------------------- stream ----


def test_stream_without_range_returns_full_file(client, storage):
    token = register_and_token(client)
    track = upload(client, token).json()
    path = storage.local_path(track["file_path"])
    file_size = path.stat().st_size
    expected = path.read_bytes()

    response = client.get(f"/tracks/{track['id']}/stream", headers=auth(token))

    assert response.status_code == 200
    assert response.headers["accept-ranges"] == "bytes"
    assert response.headers["content-length"] == str(file_size)
    assert response.content == expected


def test_stream_normal_range_returns_206(client, storage):
    token = register_and_token(client)
    track = upload(client, token).json()
    path = storage.local_path(track["file_path"])
    file_size = path.stat().st_size
    start, end = 100, 500
    expected = path.read_bytes()[start : end + 1]

    response = client.get(
        f"/tracks/{track['id']}/stream",
        headers={**auth(token), "Range": f"bytes={start}-{end}"},
    )

    assert response.status_code == 206
    assert response.headers["content-range"] == f"bytes {start}-{end}/{file_size}"
    assert response.headers["content-length"] == str(len(expected))
    assert response.content == expected


def test_stream_open_ended_range(client, storage):
    token = register_and_token(client)
    track = upload(client, token).json()
    path = storage.local_path(track["file_path"])
    file_size = path.stat().st_size
    start = 500
    expected = path.read_bytes()[start:]

    response = client.get(
        f"/tracks/{track['id']}/stream",
        headers={**auth(token), "Range": f"bytes={start}-"},
    )

    assert response.status_code == 206
    assert response.headers["content-range"] == f"bytes {start}-{file_size - 1}/{file_size}"
    assert response.headers["content-length"] == str(len(expected))
    assert response.content == expected


def test_stream_out_of_bounds_range_returns_416(client, storage):
    token = register_and_token(client)
    track = upload(client, token).json()
    path = storage.local_path(track["file_path"])
    file_size = path.stat().st_size

    response = client.get(
        f"/tracks/{track['id']}/stream",
        headers={**auth(token), "Range": f"bytes={file_size}-"},
    )

    assert response.status_code == 416
    assert response.headers["content-range"] == f"bytes */{file_size}"


# ------------------------------------------------------------------ unit ----


def test_parse_range_none_returns_full():
    assert parse_range(None, 1000) == (0, None)


def test_parse_range_normal():
    assert parse_range("bytes=100-500", 1000) == (100, 500)


def test_parse_range_open_ended():
    assert parse_range("bytes=500-", 1000) == (500, None)


def test_parse_range_end_clamped_to_file_size():
    assert parse_range("bytes=100-9999", 1000) == (100, 999)


def test_parse_range_start_beyond_size_raises():
    with pytest.raises(RangeError):
        parse_range("bytes=1000-", 1000)


def test_parse_range_invalid_unit_raises():
    with pytest.raises(RangeError):
        parse_range("items=0-10", 1000)


def test_parse_range_suffix_range_raises():
    with pytest.raises(RangeError):
        parse_range("bytes=-500", 1000)
