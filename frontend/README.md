# Melo — Frontend (HTML/CSS/JS)

Plain static frontend, no framework or build step.

## Structure
- `index.html` — home page
- `pages/` — additional pages (search, library)
- `css/` — `base.css` (reset/variables), `layout.css`, `player.css`
- `js/` — `api.js` (backend calls), `player.js` (audio controls), `app.js` (bootstrap)
- `assets/` — images, icons

## Run locally
```bash
python -m http.server 5500
# visit http://localhost:5500
```

Requires the FastAPI backend running at `http://localhost:8000` (see `js/api.js` for the base URL).
