# Melo — Backend (FastAPI)

## Structure
- `app/main.py` — FastAPI app entry point, router registration
- `app/routers` — endpoint definitions (auth, tracks, playlists, search...)
- `app/models` — SQLAlchemy ORM models
- `app/schemas` — Pydantic request/response schemas
- `app/services` — core logic (streaming, search, recommendations)
- `app/core` — config loading, JWT/security helpers
- `app/db` — database engine/session setup
- `uploads/` — local dev audio storage (not committed)
- `tests/` — backend tests

## Run locally
```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload
```

Visit `http://localhost:8000/docs` for interactive Swagger API docs.
