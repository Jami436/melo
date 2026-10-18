from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import auth, playlists, tracks

app = FastAPI(title="Melo API", version="0.1.0")

# Allow the static frontend (served separately) to call this API during dev
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten this before deploying
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    return {"status": "ok", "service": "Melo API"}


@app.get("/health")
def health():
    return {"status": "healthy"}


app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(tracks.router, prefix="/tracks", tags=["tracks"])
app.include_router(playlists.router, prefix="/playlists", tags=["playlists"])
