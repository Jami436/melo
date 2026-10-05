# Melo 

A self-built music streaming web app — a learning/portfolio project exploring the architecture behind services like Spotify (auth, audio streaming, playlists, search, and recommendations), built from scratch with my own stack, UI, and content.

> **Note:** This project does not use Spotify's catalog, branding, or proprietary assets. All audio content is either original, royalty-free, or sourced via licensed/public APIs.

---

## Tech Stack

| Layer      | Technology                          |
|------------|--------------------------------------|
| Frontend   | HTML, CSS, vanilla JavaScript        |
| Backend    | FastAPI (Python)                     |
| Database   | PostgreSQL                           |
| ORM        | SQLAlchemy                           |
| Auth       | JWT (python-jose + passlib)          |
| Storage    | Local filesystem (dev) → S3-compatible (prod) |

---

## Project Structure

```
melo/
├── frontend/                # Static HTML/CSS/JS client
│   ├── index.html
│   ├── pages/                # Additional pages (search, library, etc.)
│   ├── css/                  # Stylesheets
│   ├── js/                   # Client-side logic (api.js, player.js, app.js)
│   └── assets/                # Images, icons
│
├── backend/                  # FastAPI server
│   ├── app/
│   │   ├── main.py            # FastAPI app entry point
│   │   ├── routers/           # API route definitions (auth, tracks, playlists...)
│   │   ├── models/            # SQLAlchemy ORM models
│   │   ├── schemas/           # Pydantic request/response schemas
│   │   ├── services/          # Core logic (streaming, search, recommendations)
│   │   ├── core/               # Config, security, JWT handling
│   │   └── db/                 # DB session/engine setup
│   ├── uploads/                # Local dev audio storage (gitignored)
│   ├── tests/                   # Backend tests
│   ├── requirements.txt
│   └── .env.example
│
└── docs/                        # Architecture notes, ER diagrams, API docs
```

---

## Planned Features

- [ ] User auth (signup/login, JWT sessions)
- [ ] Audio upload + range-based streaming
- [ ] Playlists (create, edit, reorder, collaborative)
- [ ] Search (tracks, artists, albums)
- [ ] Like/save tracks and albums
- [ ] Player with queue, shuffle, repeat
- [ ] Basic recommendation engine (collaborative filtering)
- [ ] Responsive UI

---

## Getting Started

### Backend (FastAPI)
```bash
cd backend
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env            # fill in DB credentials, JWT secret, etc.
uvicorn app.main:app --reload   # runs at http://localhost:8000
```

API docs will be auto-available at `http://localhost:8000/docs` (Swagger UI).

### Frontend (static HTML/CSS/JS)
No build step needed. Either:
- Open `frontend/index.html` directly in a browser, or
- Serve it locally for a more realistic setup:
```bash
cd frontend
python -m http.server 5500      # then visit http://localhost:5500
```

Make sure the backend is running on `http://localhost:8000` — `frontend/js/api.js` points there by default.

---

## Why this project exists

Built to understand the full-stack architecture behind real-world streaming platforms — auth, media delivery, data modeling, and recommendation systems — as a hands-on learning project and portfolio piece.

## License

Personal/educational project. Not affiliated with or endorsed by Spotify.
