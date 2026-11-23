"""Tests for the /search endpoint."""

import importlib.util
from pathlib import Path
from types import SimpleNamespace

from sqlalchemy import select
from sqlalchemy.dialects import postgresql

from app.models import Track, User
from app.services.search import SEARCH_DOCUMENT_SQL, _match_and_score


def make_user(db) -> User:
    user = User(
        email="search@example.com",
        username="searcher",
        hashed_password="unused",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def make_track(
    db,
    owner_id: int,
    title: str,
    artist: str,
    album: str | None = None,
) -> Track:
    track = Track(
        title=title,
        artist=artist,
        album=album,
        duration_seconds=60,
        file_path="audio/test.mp3",
        cover_path=None,
        uploaded_by=owner_id,
    )
    db.add(track)
    db.commit()
    db.refresh(track)
    return track


def seed(db) -> tuple[int, int, int]:
    owner = make_user(db)
    first = make_track(db, owner.id, "Midnight Drive", "Neon Coast", "Nightlines")
    second = make_track(db, owner.id, "Static", "Neon Coast", "Midnight Tapes")
    third = make_track(db, owner.id, "Sunrise", "Daylight FM", "Morning")
    return first.id, second.id, third.id


def search(client, q: str, **params):
    return client.get("/search", params={"q": q, **params})


def test_empty_query_returns_empty_groups(client):
    response = search(client, "")

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["query"] == ""
    assert body["tracks"] == {"items": [], "total": 0, "page": 1, "size": 20}
    assert body["artists"] == {"items": [], "total": 0, "page": 1, "size": 20}


def test_search_matches_title_artist_and_album(client, db_session):
    first, second, third = seed(db_session)

    title_hit = search(client, "midnight drive").json()
    assert [t["id"] for t in title_hit["tracks"]["items"]] == [first]
    assert [a["name"] for a in title_hit["artists"]["items"]] == ["Neon Coast"]

    artist_hit = search(client, "neon").json()
    assert {t["id"] for t in artist_hit["tracks"]["items"]} == {first, second}
    assert artist_hit["artists"]["items"][0]["track_count"] == 2

    album_hit = search(client, "morning").json()
    assert [t["id"] for t in album_hit["tracks"]["items"]] == [third]


def test_search_is_case_insensitive(client, db_session):
    first, _, _ = seed(db_session)

    response = search(client, "MIDNIGHT DRIVE")

    assert response.status_code == 200, response.text
    assert [t["id"] for t in response.json()["tracks"]["items"]] == [first]


def test_tracks_are_ranked_by_relevance(client, db_session):
    first, second, _ = seed(db_session)

    response = search(client, "midnight")

    assert [t["id"] for t in response.json()["tracks"]["items"]] == [first, second]


def test_artists_are_grouped_with_best_matching_track(client, db_session):
    first, second, _ = seed(db_session)

    response = search(client, "midnight")
    artists = response.json()["artists"]["items"]

    assert len(artists) == 1
    assert artists[0]["name"] == "Neon Coast"
    assert artists[0]["track_count"] == 2
    assert artists[0]["top_track"]["id"] == first
    assert artists[0]["top_track"]["title"] == "Midnight Drive"

    artist_response = search(client, "static").json()
    assert artist_response["artists"]["items"][0]["top_track"]["id"] == second


def test_pagination(client, db_session):
    first, second, _ = seed(db_session)

    page_one = search(client, "neon", page=1, size=1).json()
    page_two = search(client, "neon", page=2, size=1).json()

    assert page_one["tracks"]["total"] == 2
    assert [t["id"] for t in page_one["tracks"]["items"]] == [first]
    assert [t["id"] for t in page_two["tracks"]["items"]] == [second]
    assert page_two["artists"]["items"] == []
    assert page_one["artists"]["total"] == 1


def test_no_results(client, db_session):
    seed(db_session)

    response = search(client, "zzzzzz")

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["tracks"]["items"] == []
    assert body["tracks"]["total"] == 0
    assert body["artists"]["items"] == []


def test_like_wildcards_are_literal(client, db_session):
    seed(db_session)

    for query in ("%", "100%"):
        response = search(client, query)
        assert response.status_code == 200, response.text
        assert response.json()["tracks"]["items"] == []


def test_postgres_branch_uses_full_text_and_trigrams():
    db = SimpleNamespace(
        bind=SimpleNamespace(dialect=SimpleNamespace(name="postgresql"))
    )
    match, score = _match_and_score(db, "mid night")
    sql = str(
        select(Track.id)
        .where(match)
        .order_by(score.desc())
        .compile(dialect=postgresql.dialect(), compile_kwargs={"literal_binds": True})
    )

    assert "to_tsquery" in sql
    assert "@@" in sql
    assert "similarity" in sql


def test_migration_index_matches_query_document():
    path = (
        Path(__file__).resolve().parents[1]
        / "alembic"
        / "versions"
        / "0002_search_indexes.py"
    )
    spec = importlib.util.spec_from_file_location("search_migration", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    assert module.SEARCH_DOCUMENT == SEARCH_DOCUMENT_SQL
