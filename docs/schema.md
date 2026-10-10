# Melo — Database Schema

PostgreSQL via SQLAlchemy 2.x. Schema is managed by Alembic; the initial
revision lives in `backend/alembic/versions/0001_initial_schema.py`.

Five tables:

```
users ─┬─< tracks ─┬─< playlist_tracks >─ playlists
       │           └─< liked_tracks    >─ users
       └─< playlists
```

## `users`
| column | type | notes |
| --- | --- | --- |
| `id` | int PK | surrogate key |
| `email` | varchar(255) | unique + indexed — login identifier |
| `username` | varchar(50) | unique + indexed — display/login identifier |
| `hashed_password` | varchar(255) | bcrypt hash, never the plain password |
| `created_at` | timestamptz | `DEFAULT now()` |

**Why:** both `email` and `username` are unique *and* indexed so either can be
used to look up a user in O(1). Keeping the hash in its own column (rather than
a JSON blob) keeps it easy to rotate algorithms later.

## `tracks`
| column | type | notes |
| --- | --- | --- |
| `id` | int PK | |
| `title` | varchar(255) | indexed |
| `artist` | varchar(255) | indexed |
| `album` | varchar(255) | nullable |
| `duration_seconds` | int | integer seconds — simple to sort/format |
| `file_path` | varchar(512) | relative to `UPLOAD_DIR` |
| `cover_path` | varchar(512) | nullable |
| `uploaded_by` | int FK → `users.id` | `ON DELETE CASCADE`, indexed |
| `created_at` | timestamptz | `DEFAULT now()` |

**Why:** `title`/`artist` are indexed because search filters on them. File
paths are stored **relative** to `settings.upload_dir`, so the storage root can
move (or switch to object storage) without rewriting rows. Deleting a user
cascades to their uploads.

## `playlists`
| column | type | notes |
| --- | --- | --- |
| `id` | int PK | |
| `name` | varchar(255) | |
| `owner_id` | int FK → `users.id` | `ON DELETE CASCADE`, indexed |
| `is_public` | boolean | `DEFAULT true` |
| `created_at` | timestamptz | `DEFAULT now()` |

**Why:** `is_public` drives visibility without a separate "shared" table.
`owner_id` is indexed so "all playlists for a user" is cheap.

## `playlist_tracks` (association object)
| column | type | notes |
| --- | --- | --- |
| `playlist_id` | int FK → `playlists.id` | **PK part**, `ON DELETE CASCADE` |
| `track_id` | int FK → `tracks.id` | **PK part**, `ON DELETE CASCADE` |
| `position` | int | explicit ordering |
| `added_at` | timestamptz | `DEFAULT now()` |

**Why an association object (not a plain join table):** the relationship
carries extra data (`position`, `added_at`). The composite primary key
`(playlist_id, track_id)` guarantees a track appears at most once per playlist,
and the composite index `(playlist_id, position)` makes "load this playlist in
order" a single index scan.

## `liked_tracks` (association table)
| column | type | notes |
| --- | --- | --- |
| `user_id` | int FK → `users.id` | **PK part**, `ON DELETE CASCADE` |
| `track_id` | int FK → `tracks.id` | **PK part**, `ON DELETE CASCADE` |
| `created_at` | timestamptz | `DEFAULT now()` |

**Why:** a pure many-to-many. The composite PK makes liking **idempotent**
(double-tapping the heart can't create duplicates), and `created_at` lets the
UI sort "Liked Songs" by when they were saved.

## Cross-cutting decisions
- **`created_at` uses `server_default=now()`**, so timestamps come from
  PostgreSQL and are consistent even for rows inserted outside the ORM.
- **`ON DELETE CASCADE` on every foreign key**, backed by ORM-level
  `cascade="all, delete-orphan"`, so a single delete cleans up children.
- **Timestamps are `timezone=True`** (Postgres `timestamptz`) to avoid
  ambiguity across servers.
- **No naming convention** is imposed on constraints; indexes use SQLAlchemy's
  default `ix_<table>_<column>` names.

## Common commands
```bash
cd backend
alembic upgrade head                                  # apply migrations
alembic downgrade -1                                  # roll back one revision
alembic revision --autogenerate -m "describe change"  # new migration from models
alembic history                                       # list revisions
alembic current                                       # show applied revision
```
