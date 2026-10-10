"""Application settings.

Every value is read from environment variables, falling back to the
``backend/.env`` file (see ``.env.example`` for the expected keys). Keeping a
single cached ``settings`` object means the rest of the app can simply do
``from app.core.config import settings`` without touching the filesystem again.
"""

from functools import lru_cache
from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# backend/app/core/config.py -> parents[2] == backend/
BACKEND_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    """Typed view over the environment. Field names map case-insensitively to
    env vars (``DATABASE_URL`` -> ``database_url``)."""

    # Database
    database_url: str = "postgresql://user:password@localhost:5432/melo"

    # Auth (used by the security helpers later)
    jwt_secret: str = "change_this_to_a_random_secret"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60

    # Where uploaded audio/cover files are stored on disk
    upload_dir: Path = BACKEND_DIR / "uploads"

    model_config = SettingsConfigDict(
        env_file=BACKEND_DIR / ".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",  # ignore unrelated keys in .env
    )

    @field_validator("database_url", mode="after")
    @classmethod
    def _pin_psycopg2_driver(cls, value: str) -> str:
        """Make sure the URL names the psycopg2 driver we install.

        SQLAlchemy 2.1 resolves a bare ``postgresql://`` URL to the psycopg
        (v3) driver. This project ships psycopg2-binary, so we rewrite the
        scheme when no driver is specified."""
        for prefix in ("postgresql://", "postgres://"):
            if value.startswith(prefix):
                return "postgresql+psycopg2://" + value[len(prefix):]
        return value

    @field_validator("upload_dir", mode="after")
    @classmethod
    def _resolve_upload_dir(cls, value: Path) -> Path:
        """Make relative paths (e.g. ``./uploads``) absolute against backend/,
        so behaviour never depends on the process working directory."""
        return value if value.is_absolute() else (BACKEND_DIR / value).resolve()


@lru_cache
def get_settings() -> Settings:
    """Return a single cached Settings instance (cheap, import-safe)."""
    return Settings()


settings = get_settings()
