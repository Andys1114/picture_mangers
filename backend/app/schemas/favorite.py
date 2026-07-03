"""Favorite (collection) request/response schemas.

List responses carry an ``item_count`` (denormalized count of posts in the
collection) but not the posts themselves — detail responses carry the items.
No ``fav_count`` anywhere: per the grilling decision, "favorited" state is
derived from ``favorite_items`` membership, never a counter on Post.
"""
from __future__ import annotations

from pydantic import BaseModel, Field


class FavoriteResponse(BaseModel):
    """List-item shape — minimal, no posts."""

    id: int
    name: str
    item_count: int


class FavoriteCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=128)


class FavoriteItemResponse(BaseModel):
    post_id: int
    position: int


class FavoriteDetailResponse(BaseModel):
    """Single-collection detail — includes the member posts."""

    id: int
    name: str
    items: list[FavoriteItemResponse]


class FavoriteItemReorderRequest(BaseModel):
    position: int = Field(ge=0)


class StarToggleResponse(BaseModel):
    """Result of POST /api/posts/{id}/favorite — whether the post is now in
    the default (star) collection."""

    favorited: bool
