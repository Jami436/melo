"""ORM models.

Importing this package registers every table on ``Base.metadata``, which is
what Alembic autogenerate inspects. Keep the imports even if "unused".
"""

from app.models.liked_track import LikedTrack
from app.models.playlist import Playlist, PlaylistTrack
from app.models.track import Track
from app.models.user import User

__all__ = ["User", "Track", "Playlist", "PlaylistTrack", "LikedTrack"]
