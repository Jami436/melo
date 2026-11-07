"""Tests for playlists, ownership checks and liked songs."""

from app.models import Track


def register(client, *, email: str, username: str) -> int:
    response = client.post(
        "/auth/signup",
        json={"email": email, "username": username, "password": "supersecret"},
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


def login(client, *, email: str) -> str:
    response = client.post(
        "/auth/login", json={"email": email, "password": "supersecret"}
    )
    assert response.status_code == 200, response.text
    return response.json()["access_token"]


def auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def make_track(db, owner_id: int, title: str = "Song") -> Track:
    track = Track(
        title=title,
        artist="Artist",
        album=None,
        duration_seconds=60,
        file_path=f"audio/{title.replace(' ', '-').lower()}.mp3",
        cover_path=None,
        uploaded_by=owner_id,
    )
    db.add(track)
    db.commit()
    db.refresh(track)
    return track


def create_playlist(client, token: str, name: str = "Mix") -> dict:
    response = client.post(
        "/playlists", json={"name": name, "is_public": True}, headers=auth(token)
    )
    assert response.status_code == 201, response.text
    return response.json()


def two_users(client):
    owner_id = register(client, email="owner@example.com", username="owner")
    other_id = register(client, email="other@example.com", username="other")
    return (
        owner_id,
        login(client, email="owner@example.com"),
        other_id,
        login(client, email="other@example.com"),
    )


# -------------------------------------------------------------- summaries ----


def test_list_returns_only_current_users_playlists(client):
    _, owner_token, _, other_token = two_users(client)
    mine = create_playlist(client, owner_token, "Mine")
    create_playlist(client, other_token, "Theirs")

    response = client.get("/playlists", headers=auth(owner_token))

    assert response.status_code == 200
    assert [item["id"] for item in response.json()] == [mine["id"]]


def test_create_sets_owner_and_track_count(client):
    owner_id, owner_token, _, _ = two_users(client)
    playlist = create_playlist(client, owner_token, "  Road Trip  ")

    assert playlist["name"] == "Road Trip"
    assert playlist["owner_id"] == owner_id
    assert playlist["track_count"] == 0


# ---------------------------------------------------------------- read ----


def test_get_playlist_by_non_owner_is_forbidden(client):
    _, owner_token, _, other_token = two_users(client)
    playlist = create_playlist(client, owner_token)

    response = client.get(f"/playlists/{playlist['id']}", headers=auth(other_token))

    assert response.status_code == 403


def test_get_missing_playlist_is_not_found(client):
    _, owner_token, _, _ = two_users(client)

    response = client.get("/playlists/999", headers=auth(owner_token))

    assert response.status_code == 404


def test_owner_can_get_playlist_with_tracks_in_order(client, db_session):
    owner_id, owner_token, _, _ = two_users(client)
    playlist = create_playlist(client, owner_token)
    first = make_track(db_session, owner_id, "First")
    second = make_track(db_session, owner_id, "Second")

    for track in (first, second):
        response = client.post(
            f"/playlists/{playlist['id']}/tracks",
            json={"track_id": track.id},
            headers=auth(owner_token),
        )
        assert response.status_code == 201, response.text

    response = client.get(f"/playlists/{playlist['id']}", headers=auth(owner_token))

    assert response.status_code == 200
    body = response.json()
    assert body["track_count"] == 2
    assert [track["id"] for track in body["tracks"]] == [first.id, second.id]


# --------------------------------------------------------------- update ----


def test_update_by_non_owner_is_forbidden(client):
    _, owner_token, _, other_token = two_users(client)
    playlist = create_playlist(client, owner_token, "Original")

    response = client.patch(
        f"/playlists/{playlist['id']}",
        json={"name": "Hijacked"},
        headers=auth(other_token),
    )

    assert response.status_code == 403
    owner_view = client.get(f"/playlists/{playlist['id']}", headers=auth(owner_token))
    assert owner_view.json()["name"] == "Original"


def test_owner_can_rename_and_change_visibility(client):
    _, owner_token, _, _ = two_users(client)
    playlist = create_playlist(client, owner_token, "Original")

    response = client.patch(
        f"/playlists/{playlist['id']}",
        json={"name": "Renamed", "is_public": False},
        headers=auth(owner_token),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "Renamed"
    assert body["is_public"] is False


# --------------------------------------------------------------- delete ----


def test_delete_by_non_owner_is_forbidden(client):
    _, owner_token, _, other_token = two_users(client)
    playlist = create_playlist(client, owner_token)

    response = client.delete(
        f"/playlists/{playlist['id']}", headers=auth(other_token)
    )

    assert response.status_code == 403
    assert (
        client.get(f"/playlists/{playlist['id']}", headers=auth(owner_token)).status_code
        == 200
    )


def test_owner_can_delete_playlist(client):
    _, owner_token, _, _ = two_users(client)
    playlist = create_playlist(client, owner_token)

    response = client.delete(
        f"/playlists/{playlist['id']}", headers=auth(owner_token)
    )

    assert response.status_code == 204
    assert (
        client.get(f"/playlists/{playlist['id']}", headers=auth(owner_token)).status_code
        == 404
    )


# ----------------------------------------------------------- playlist tracks ----


def test_add_track_by_non_owner_is_forbidden(client, db_session):
    owner_id, owner_token, _, other_token = two_users(client)
    playlist = create_playlist(client, owner_token)
    track = make_track(db_session, owner_id)

    response = client.post(
        f"/playlists/{playlist['id']}/tracks",
        json={"track_id": track.id},
        headers=auth(other_token),
    )

    assert response.status_code == 403
    owner_view = client.get(f"/playlists/{playlist['id']}", headers=auth(owner_token))
    assert owner_view.json()["tracks"] == []


def test_add_missing_track_is_not_found(client):
    _, owner_token, _, _ = two_users(client)
    playlist = create_playlist(client, owner_token)

    response = client.post(
        f"/playlists/{playlist['id']}/tracks",
        json={"track_id": 999},
        headers=auth(owner_token),
    )

    assert response.status_code == 404


def test_adding_same_track_twice_conflicts(client, db_session):
    owner_id, owner_token, _, _ = two_users(client)
    playlist = create_playlist(client, owner_token)
    track = make_track(db_session, owner_id)
    url = f"/playlists/{playlist['id']}/tracks"

    assert (
        client.post(url, json={"track_id": track.id}, headers=auth(owner_token)).status_code
        == 201
    )
    response = client.post(url, json={"track_id": track.id}, headers=auth(owner_token))

    assert response.status_code == 409


def test_remove_track_by_non_owner_is_forbidden(client, db_session):
    owner_id, owner_token, _, other_token = two_users(client)
    playlist = create_playlist(client, owner_token)
    track = make_track(db_session, owner_id)
    client.post(
        f"/playlists/{playlist['id']}/tracks",
        json={"track_id": track.id},
        headers=auth(owner_token),
    )

    response = client.delete(
        f"/playlists/{playlist['id']}/tracks/{track.id}",
        headers=auth(other_token),
    )

    assert response.status_code == 403
    owner_view = client.get(f"/playlists/{playlist['id']}", headers=auth(owner_token))
    assert [t["id"] for t in owner_view.json()["tracks"]] == [track.id]


def test_owner_can_remove_track_and_positions_compact(client, db_session):
    owner_id, owner_token, _, _ = two_users(client)
    playlist = create_playlist(client, owner_token)
    first = make_track(db_session, owner_id, "First")
    second = make_track(db_session, owner_id, "Second")
    third = make_track(db_session, owner_id, "Third")
    for track in (first, second, third):
        client.post(
            f"/playlists/{playlist['id']}/tracks",
            json={"track_id": track.id},
            headers=auth(owner_token),
        )

    response = client.delete(
        f"/playlists/{playlist['id']}/tracks/{second.id}",
        headers=auth(owner_token),
    )

    assert response.status_code == 204
    body = client.get(
        f"/playlists/{playlist['id']}", headers=auth(owner_token)
    ).json()
    assert [t["id"] for t in body["tracks"]] == [first.id, third.id]


# --------------------------------------------------------------- reorder ----


def test_reorder_by_non_owner_is_forbidden(client, db_session):
    owner_id, owner_token, _, other_token = two_users(client)
    playlist = create_playlist(client, owner_token)
    first = make_track(db_session, owner_id, "First")
    second = make_track(db_session, owner_id, "Second")
    for track in (first, second):
        client.post(
            f"/playlists/{playlist['id']}/tracks",
            json={"track_id": track.id},
            headers=auth(owner_token),
        )

    response = client.put(
        f"/playlists/{playlist['id']}/reorder",
        json={"track_ids": [second.id, first.id]},
        headers=auth(other_token),
    )

    assert response.status_code == 403
    body = client.get(
        f"/playlists/{playlist['id']}", headers=auth(owner_token)
    ).json()
    assert [t["id"] for t in body["tracks"]] == [first.id, second.id]


def test_owner_can_reorder(client, db_session):
    owner_id, owner_token, _, _ = two_users(client)
    playlist = create_playlist(client, owner_token)
    first = make_track(db_session, owner_id, "First")
    second = make_track(db_session, owner_id, "Second")
    third = make_track(db_session, owner_id, "Third")
    for track in (first, second, third):
        client.post(
            f"/playlists/{playlist['id']}/tracks",
            json={"track_id": track.id},
            headers=auth(owner_token),
        )

    response = client.put(
        f"/playlists/{playlist['id']}/reorder",
        json={"track_ids": [third.id, first.id, second.id]},
        headers=auth(owner_token),
    )

    assert response.status_code == 200
    assert [t["id"] for t in response.json()["tracks"]] == [
        third.id,
        first.id,
        second.id,
    ]


def test_owner_can_reorder_with_bare_list(client, db_session):
    owner_id, owner_token, _, _ = two_users(client)
    playlist = create_playlist(client, owner_token)
    first = make_track(db_session, owner_id, "First")
    second = make_track(db_session, owner_id, "Second")
    for track in (first, second):
        client.post(
            f"/playlists/{playlist['id']}/tracks",
            json={"track_id": track.id},
            headers=auth(owner_token),
        )

    response = client.put(
        f"/playlists/{playlist['id']}/reorder",
        json=[second.id, first.id],
        headers=auth(owner_token),
    )

    assert response.status_code == 200
    assert [t["id"] for t in response.json()["tracks"]] == [second.id, first.id]


def test_reorder_rejects_incomplete_or_duplicate_lists(client, db_session):
    owner_id, owner_token, _, _ = two_users(client)
    playlist = create_playlist(client, owner_token)
    first = make_track(db_session, owner_id, "First")
    second = make_track(db_session, owner_id, "Second")
    for track in (first, second):
        client.post(
            f"/playlists/{playlist['id']}/tracks",
            json={"track_id": track.id},
            headers=auth(owner_token),
        )
    url = f"/playlists/{playlist['id']}/reorder"

    incomplete = client.put(
        url, json={"track_ids": [first.id]}, headers=auth(owner_token)
    )
    duplicate = client.put(
        url,
        json={"track_ids": [first.id, first.id]},
        headers=auth(owner_token),
    )

    assert incomplete.status_code == 400
    assert duplicate.status_code == 400


# ----------------------------------------------------------------- likes ----


def test_like_is_idempotent_and_lists_for_current_user(client, db_session):
    owner_id, owner_token, _, other_token = two_users(client)
    track = make_track(db_session, owner_id, "Loved")
    url = f"/tracks/{track.id}/like"

    first = client.post(url, headers=auth(owner_token))
    second = client.post(url, headers=auth(owner_token))

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json() == {"track_id": track.id, "liked": True}

    mine = client.get("/me/likes", headers=auth(owner_token))
    theirs = client.get("/me/likes", headers=auth(other_token))
    assert [t["id"] for t in mine.json()] == [track.id]
    assert theirs.json() == []


def test_unlike_removes_track_from_likes(client, db_session):
    owner_id, owner_token, _, _ = two_users(client)
    track = make_track(db_session, owner_id, "Loved")
    client.post(f"/tracks/{track.id}/like", headers=auth(owner_token))

    response = client.delete(
        f"/tracks/{track.id}/like", headers=auth(owner_token)
    )

    assert response.status_code == 204
    assert client.get("/me/likes", headers=auth(owner_token)).json() == []


def test_like_missing_track_is_not_found(client):
    _, owner_token, _, _ = two_users(client)

    response = client.post("/tracks/999/like", headers=auth(owner_token))

    assert response.status_code == 404


def test_likes_require_authentication(client, db_session):
    owner_id, _, _, _ = two_users(client)
    track = make_track(db_session, owner_id, "Loved")

    assert client.get("/me/likes").status_code == 401
    assert client.post(f"/tracks/{track.id}/like").status_code == 401
