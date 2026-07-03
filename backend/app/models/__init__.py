"""ORM models package.

Importing this module registers every model on Base.metadata so Alembic
autogenerate and migrations see the full schema.
"""
from app.models.base import Base, TimestampMixin
from app.models.favorite import Favorite, FavoriteItem
from app.models.post import Post
from app.models.scan_history import ScanHistory
from app.models.tag import PostTag, Tag, TagImplication
from app.models.user import Session, User

__all__ = [
    "Base",
    "TimestampMixin",
    "Post",
    "ScanHistory",
    "Tag",
    "PostTag",
    "TagImplication",
    "Favorite",
    "FavoriteItem",
    "User",
    "Session",
]
