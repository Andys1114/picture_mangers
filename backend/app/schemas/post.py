"""Post / Tag response schemas."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class TagResponse(BaseModel):
    id: int
    name: str
    category: str
    post_count: int


class PostSummaryResponse(BaseModel):
    """List-item shape — minimal fields, no full tag set (reduces payload)."""

    id: int
    preview_path: str
    width: int
    height: int
    rating: str
    is_animated: bool
    # Whether the current user has this post in their default favorite.
    # Favorites API lands in a later subtask; until then this is always False
    # (favorited state is derived from favorite_items membership, never a count).
    favorite: bool = False


class PostDetailResponse(PostSummaryResponse):
    """Single-post detail — full fields + expanded tag set."""

    file_path: str
    thumb_path: str
    source_site: str | None = None
    source_url: str | None = None
    md5: str
    created_at: datetime
    tags: list[TagResponse]


class PageMeta(BaseModel):
    page: int
    total: int


class PostListResponse(BaseModel):
    """Success envelope for the posts list: {data, meta}."""

    data: list[PostSummaryResponse]
    meta: PageMeta
