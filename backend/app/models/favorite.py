"""Favorite (collection) and FavoriteItem models."""
from __future__ import annotations

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class Favorite(TimestampMixin, Base):
    """A named collection of posts (a 'playlist' of images)."""

    __tablename__ = "favorites"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)


class FavoriteItem(Base):
    """A post's membership in a favorite, with an ordering position."""

    __tablename__ = "favorite_items"

    favorite_id: Mapped[int] = mapped_column(
        ForeignKey("favorites.id", ondelete="CASCADE"), primary_key=True
    )
    post_id: Mapped[int] = mapped_column(
        ForeignKey("posts.id", ondelete="CASCADE"), primary_key=True
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
