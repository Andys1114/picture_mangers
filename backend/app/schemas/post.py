"""Post / Tag response schemas."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class TagResponse(BaseModel):
    id: int
    name: str
    category: str
    post_count: int
    # Deprecated tags stay attached to posts but clients should de-emphasize
    # them; defaults False so older payload builders remain valid.
    is_deprecated: bool = False


class PostSummaryResponse(BaseModel):
    """List-item shape — minimal fields, no full tag set (reduces payload)."""

    id: int
    preview_path: str
    width: int
    height: int
    rating: str
    is_animated: bool
    # True when the post is in the default (star) collection — derived from
    # favorite_items membership, never a count (grilling decision).
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


class PostUpdateRequest(BaseModel):
    """Partial update for PATCH /api/posts/{id}.

    ``tags`` (when present) is a full-replacement tag-name list — the post's
    tag set becomes exactly this (existing tags not in the list are removed,
    new ones are added via the implication-materializing tag_post). ``rating``
    is optional. Either field may be omitted to leave it untouched.
    """

    tags: list[str] | None = None
    rating: str | None = Field(default=None, pattern=r"^(safe|questionable|explicit)$")


class PostNextResponse(BaseModel):
    """Prev/next post ids for the detail-page keyboard navigation.

    Computed over the global id-desc view (excluding duplicates), independent
    of any tag filter — the detail page navigates the whole gallery. Safe mode
    (when on for the session) skips non-safe posts, matching the gallery.
    """

    prev_id: int | None
    next_id: int | None
