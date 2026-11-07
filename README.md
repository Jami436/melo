# Melo

A self-built music streaming web app — a learning/portfolio project exploring the architecture behind services like Spotify (auth, audio streaming, playlists, search, and recommendations), built from scratch with my own stack, UI, and content.

> **Note:** This project does not use Spotify's catalog, branding, or proprietary assets. All audio content is either original, royalty-free, or sourced via licensed/public APIs.

---

## Status

The core listening flow works end-to-end: accounts, audio uploads, range-based streaming, playlists, liked songs, and a persistent player. Search currently runs client-side over the loaded catalog; server-side search and recommendations are still on the roadmap.

---

## Tech Stack

| Layer          | Technology                                   |
|----------------|----------------------------------------------|
| Frontend       | HTML, CSS, vanilla JavaScript (no build step) |
| Backend        | FastAPI (Python 3.11+)                       |
| Database       | PostgreSQL                                   |
| ORM            | SQLAlchemy 2.x                               |
| Migrations     | Alembic                                      |
| Auth           | JWT (python-jose + passlib/bcrypt)           |
| Storage        | Local filesystem behind a swappable backend  |
| Audio metadata | Mutagen                                      |
| Testing        | pytest + httpx (in-memory SQLite)            |

---

## Features

### Accounts & sessions
- Signup and login with hashed passwords (bcrypt).
- JWT bearer tokens; protected pages redirect to login when signed out.
- `GET /auth/me` for the current user; logout clears the client token.

### Uploads & streaming
- Upload MP3, WAV, OGG, or FLAC (25 MB limit) with an optional cover image (5 MB limit).
- Duration is read automatically with Mutagen; files are stored under generated UUID names.
- Audio streams with HTTP Range support (`206 Partial Content`) so seeking works.
- Uploaded tracks can be deleted by their uploader (ownership enforced).

### Playlists
- Create, list, rename, change visibility, and delete playlists.
- Add and remove tracks; positions stay compact after removal.
- Reorder a playlist with an ordered list of track IDs.
- Every playlist-by-id endpoint is owner-scoped (403 for non-owners, 404 for missing).

### Liked songs
- Like/unlike any track (idempotent); `GET /me/likes` returns the current user's saved tracks.
- Heart toggles appear on track rows, cards, and the player bar.

### Player & UI
- Persistent bottom player with queue playback, previous/next, shuffle, repeat, seek, and volume.
- Home page with recent tracks and playlists.
- Library page with **Playlists** / **Liked Songs** tabs, a create-playlist modal, and per-track add-to-playlist menus.
- Dedicated playlist page that plays tracks in order and allows removing them.
- Client-side search over the loaded catalog (title/artist).
- Placeholder cover art, keyboard shortcuts (`/` to search, space to play/pause), and accessible dialogs.

---

## API Overview

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/auth/signup` | — | Create an account |
| POST | `/auth/login` | — | Get a JWT access token |
| GET | `/auth/me` | Yes | Current user |
| POST | `/tracks/upload` | Yes | Upload a track (+ optional cover) |
| GET | `/tracks` | — | Paginated track list |
| GET | `/tracks/{id}` | — | Track metadata |
| GET | `/tracks/{id}/stream` | — | Audio stream with Range support |
| GET | `/tracks/covers/{path}` | — | Serve a cover image |
| DELETE | `/tracks/{id}` | Yes | Delete your own track |
| POST | `/tracks/{id}/like` | Yes | Like a track (idempotent) |
| DELETE | `/tracks/{id}/like` | Yes | Unlike a track |
| GET | `/me/likes` | Yes | Your liked songs |
| GET | `/playlists` | Yes | Your playlists |
| POST | `/playlists` | Yes | Create a playlist |
| GET | `/playlists/{id}` | Yes | Playlist with ordered tracks |
| PATCH | `/playlists/{id}` | Yes | Rename / change visibility |
| DELETE | `/playlists/{id}` | Yes | Delete a playlist |
| POST | `/playlists/{id}/tracks` | Yes | Add a track |
| DELETE | `/playlists/{id}/tracks/{track_id}` | Yes | Remove a track |
| PUT | `/playlists/{id}/reorder` | Yes | Reorder (`{"track_ids": [...]}` or a bare array) |

Interactive docs are available at `http://localhost:8000/docs` while the backend runs.

---

## Project Structure

```
melo/
├── frontend/                    # Static HTML/CSS/JS client
│   ├── index.html               # Home
│   ├── pages/                   # login, signup, search, library, playlist
│   ├── css/                     # base.css, layout.css, player.css
│   ├── js/                      # api.js, player.js, app.js
│   └── assets/                  # Images, icons
│
├── backend/                     # FastAPI server
│   ├── app/
│   │   ├── main.py              # App entry point + router registration
│   │   ├── dependencies.py      # get_current_user (JWT -> User)
│   │   ├── routers/             # auth, me, tracks, playlists
│   │   ├── models/              # User, Track, Playlist, PlaylistTrack, LikedTrack
│   │   ├── schemas/             # Pydantic request/response models
│   │   ├── services/            # storage.py, streaming.py
│   │   ├── core/                # config.py, security.py
│   │   └── db/                  # Base, engine/session, get_db
│   ├── alembic/                 # Migrations (0001_initial_schema)
│   ├── uploads/                 # Local dev audio storage (gitignored)
│   ├── tests/                   # test_auth, test_tracks, test_playlists
│   ├── requirements.txt
│   └── .env.example
│
└── docs/
    └── schema.md                # Database schema and design notes
```

---

## Roadmap

- [x] User auth (signup/login, JWT sessions)
- [x] Audio upload + range-based streaming
- [x] Playlists (create, edit, delete, add/remove, reorder)
- [x] Like/save tracks
- [x] Player with queue, shuffle, repeat
- [x] Library, search, and playlist pages
- [ ] Collaborative playlists and public playlist sharing
- [ ] Server-side search endpoint (currently client-side over the loaded catalog)
- [ ] Basic recommendation engine (collaborative filtering)
- [ ] Album support and album likes
- [ ] Responsive/mobile polish
- [ ] S3-compatible storage backend
- [ ] Hardened auth (httpOnly cookies / refresh tokens)
- [ ] CI pipeline

---

## Getting Started

### Prerequisites
- Python 3.11+
- PostgreSQL running locally (create an empty database, e.g. `melo`)

### Backend (FastAPI)
```bash
cd backend
python -m venv venv
venv\Scripts\activate            # Windows
# source venv/bin/activate       # macOS/Linux
pip install -r requirements.txt
cp .env.example .env             # set DATABASE_URL, JWT_SECRET, etc.
alembic upgrade head             # create the tables
uvicorn app.main:app --reload    # http://localhost:8000
```

### Frontend (static HTML/CSS/JS)
No build step needed. Either open `frontend/index.html` directly, or serve it:
```bash
cd frontend
python -m http.server 5500       # http://localhost:5500
```

The client calls `http://localhost:8000` by default (`frontend/js/api.js`).

---

## Tests

The backend suite runs against an in-memory SQLite database, so PostgreSQL is not required for tests:

```bash
cd backend
pytest -q
```

Current coverage: 55 tests across auth, uploads/streaming, playlists (including ownership checks), and liked songs.

---

## Database

Schema and design rationale live in [`docs/schema.md`](docs/schema.md). Migrations are managed with Alembic from `backend/`:

```bash
alembic upgrade head                                  # apply migrations
alembic downgrade -1                                  # roll back one revision
alembic revision --autogenerate -m "describe change"  # new migration
```

---

## Notes

- Uploads are validated by extension and size, saved under generated names, and stored relative to `UPLOAD_DIR`.
- Playlist access is owner-scoped; track deletion is restricted to the uploader.
- The JWT is kept in `localStorage` for development. Moving to httpOnly cookies is on the roadmap.

---

## Why this project exists

Built to understand the full-stack architecture behind real-world streaming platforms — auth, media delivery, data modeling, and recommendation systems — as a hands-on learning project and portfolio piece.

## License

Personal/educational project. Not affiliated with or endorsed by Spotify.
