"""Favorite (collection) and FavoriteItem models."""
from __future__ import annotations

from sqlalchemy import ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class Favorite(TimestampMixin, Base):
    """A named collection of posts (a 'playlist' of images)."""

    __tablename__ = "favorites"

    id: Mapped[int] = mapped_column(primary_key=True)
    # Names identify collections (the default/star collection is looked up by
    # name), so they must be unique. Enforced via a unique INDEX rather than a
    # table constraint: adding a constraint on SQLite needs a batch-mode table
    # rebuild, and dropping the old table under PRAGMA foreign_keys=ON fires
    # favorite_items' ON DELETE CASCADE, wiping memberships.
    name: Mapped[str] = mapped_column(String(128), nullable=False)

    __table_args__ = (Index("ux_favorites_name", "name", unique=True),)


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

    # The composite PK only covers favorite_id-prefixed lookups; membership
    # checks and the star toggle query by post_id.
    __table_args__ = (Index("ix_favorite_items_post_id", "post_id"),)
