"""Search helpers used by GET /search.

PostgreSQL searches a weighted tsvector backed by a GIN expression index and
adds pg_trgm similarity so small typos still match. The in-memory SQLite test
database gets an equivalent lower()/LIKE scoring path.
"""

import re

from sqlalchemy import case, func, literal_column, or_, select
from sqlalchemy.orm import Session

from app.models import Track
from app.schemas.search import ArtistHit, ArtistPage, SearchResponse
from app.schemas.track import TrackPage, TrackOut

SEARCH_DOCUMENT_SQL = (
    "setweight(to_tsvector('simple', coalesce(title, '')), 'A') || "
    "setweight(to_tsvector('simple', coalesce(artist, '')), 'B') || "
    "setweight(to_tsvector('simple', coalesce(album, '')), 'C')"
)

_MAX_TOKENS = 8
_TS_CONFIG = literal_column("'simple'")
_TS_EMPTY = literal_column("''")


def _tokens(query: str) -> list[str]:
    return re.findall(r"[^\W_]+", query, flags=re.UNICODE)[:_MAX_TOKENS]


def _like_value(query: str) -> str:
    return query.lower().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def _search_document():
    def weighted(column, weight: str):
        return func.setweight(
            func.to_tsvector(_TS_CONFIG, func.coalesce(column, _TS_EMPTY)),
            literal_column(f"'{weight}'"),
        )

    document = weighted(Track.title, "A")
    document = document.op("||")(weighted(Track.artist, "B"))
    return document.op("||")(weighted(Track.album, "C"))


def _match_and_score(db: Session, query: str):
    if db.bind.dialect.name == "postgresql":
        tsquery = func.to_tsquery(
            _TS_CONFIG, " & ".join(f'"{token}":*' for token in _tokens(query))
        )
        document = _search_document()
        similarity = func.greatest(
            func.similarity(Track.title, query),
            func.similarity(Track.artist, query),
            func.coalesce(func.similarity(Track.album, query), 0.0),
        )
        match = or_(
            document.op("@@")(tsquery),
            Track.title.op("%")(query),
            Track.artist.op("%")(query),
            Track.album.op("%")(query),
        )
        return match, func.ts_rank(document, tsquery) + similarity * 0.25

    exact = query.lower()
    escaped = _like_value(query)
    prefix = f"{escaped}%"
    contains = f"%{escaped}%"
    title, artist, album = (
        func.lower(Track.title),
        func.lower(Track.artist),
        func.lower(Track.album),
    )
    match = or_(
        title.like(contains, escape="\\"),
        artist.like(contains, escape="\\"),
        album.like(contains, escape="\\"),
    )
    score = case(
        (title == exact, 5.0),
        (artist == exact, 4.0),
        (album == exact, 3.0),
        (title.like(prefix, escape="\\"), 2.5),
        (artist.like(prefix, escape="\\"), 2.0),
        (album.like(prefix, escape="\\"), 1.5),
        (title.like(contains, escape="\\"), 1.0),
        (artist.like(contains, escape="\\"), 0.75),
        (album.like(contains, escape="\\"), 0.5),
        else_=0.0,
    )
    return match, score


def _track_page(db: Session, match, score, page: int, size: int) -> TrackPage:
    total = db.scalar(select(func.count()).select_from(Track).where(match)) or 0
    rows = db.scalars(
        select(Track)
        .where(match)
        .order_by(score.desc(), Track.id.asc())
        .offset((page - 1) * size)
        .limit(size)
    ).all()
    return TrackPage(items=list(rows), total=total, page=page, size=size)


def _artist_page(db: Session, match, score, page: int, size: int) -> ArtistPage:
    ranked = (
        select(
            Track.id.label("id"),
            Track.title.label("title"),
            Track.artist.label("artist"),
            Track.album.label("album"),
            Track.duration_seconds.label("duration_seconds"),
            Track.file_path.label("file_path"),
            Track.cover_path.label("cover_path"),
            Track.uploaded_by.label("uploaded_by"),
            Track.created_at.label("created_at"),
            score.label("score"),
            func.row_number()
            .over(
                partition_by=func.lower(Track.artist),
                order_by=(score.desc(), Track.id.asc()),
            )
            .label("row_number"),
        )
        .where(match)
        .subquery("ranked_tracks")
    )
    totals = (
        select(
            func.lower(ranked.c.artist).label("artist_key"),
            func.max(ranked.c.score).label("best_score"),
            func.count().label("track_count"),
        )
        .group_by(func.lower(ranked.c.artist))
        .subquery("artist_totals")
    )
    total = db.scalar(select(func.count()).select_from(totals)) or 0
    rows = db.execute(
        select(
            ranked.c.id,
            ranked.c.title,
            ranked.c.artist,
            ranked.c.album,
            ranked.c.duration_seconds,
            ranked.c.file_path,
            ranked.c.cover_path,
            ranked.c.uploaded_by,
            ranked.c.created_at,
            totals.c.track_count,
        )
        .join(totals, func.lower(ranked.c.artist) == totals.c.artist_key)
        .where(ranked.c.row_number == 1)
        .order_by(
            totals.c.best_score.desc(),
            totals.c.track_count.desc(),
            totals.c.artist_key.asc(),
        )
        .offset((page - 1) * size)
        .limit(size)
    ).all()
    items = [
        ArtistHit(
            name=row.artist,
            track_count=row.track_count,
            top_track=TrackOut(
                id=row.id,
                title=row.title,
                artist=row.artist,
                album=row.album,
                duration_seconds=row.duration_seconds,
                file_path=row.file_path,
                cover_path=row.cover_path,
                uploaded_by=row.uploaded_by,
                created_at=row.created_at,
            ),
        )
        for row in rows
    ]
    return ArtistPage(items=items, total=total, page=page, size=size)


def search(db: Session, query: str, page: int, size: int) -> SearchResponse:
    q = query.strip()
    if not q or not _tokens(q):
        return SearchResponse(
            query=q,
            tracks=TrackPage(items=[], total=0, page=page, size=size),
            artists=ArtistPage(items=[], total=0, page=page, size=size),
        )

    match, score = _match_and_score(db, q)
    return SearchResponse(
        query=q,
        tracks=_track_page(db, match, score, page, size),
        artists=_artist_page(db, match, score, page, size),
    )
