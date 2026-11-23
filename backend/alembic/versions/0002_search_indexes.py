"""search indexes

Adds the weighted tsvector GIN index and pg_trgm indexes used by GET /search.

Revision ID: 0002_search_indexes
Revises: 0001_initial_schema
Create Date: 2026-11-23
"""

from alembic import op

revision = "0002_search_indexes"
down_revision = "0001_initial_schema"
branch_labels = None
depends_on = None

SEARCH_DOCUMENT = (
    "setweight(to_tsvector('simple', coalesce(title, '')), 'A') || "
    "setweight(to_tsvector('simple', coalesce(artist, '')), 'B') || "
    "setweight(to_tsvector('simple', coalesce(album, '')), 'C')"
)


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
    op.execute(
        "CREATE INDEX ix_tracks_search_document ON tracks USING GIN ("
        + SEARCH_DOCUMENT
        + ")"
    )
    for column in ("title", "artist", "album"):
        op.create_index(
            f"ix_tracks_{column}_trgm",
            "tracks",
            [column],
            postgresql_using="gin",
            postgresql_ops={column: "gin_trgm_ops"},
        )


def downgrade() -> None:
    for column in ("title", "artist", "album"):
        op.drop_index(f"ix_tracks_{column}_trgm", table_name="tracks")
    op.execute("DROP INDEX IF EXISTS ix_tracks_search_document")
