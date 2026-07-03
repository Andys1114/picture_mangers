"""Tag request/response schemas.

`TagResponse` is shared with the post detail endpoint (a post's tags are part
of its detail payload), so it lives in `schemas/post.py` and is re-exported
here for cohesion. This module adds the tag-management request shapes and the
implication-tree list node.
"""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from app.schemas.post import TagResponse  # noqa: F401 — re-exported for callers

# Valid tag categories (CONTEXT.md「标签」+ grilling decisions).
_CATEGORY_PATTERN = r"^(general|character|copyright|artist|meta)$"


class TagCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    category: str = Field(default="general", pattern=_CATEGORY_PATTERN)


class TagUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    category: str | None = Field(default=None, pattern=_CATEGORY_PATTERN)


class TagTreeNode(BaseModel):
    """An implication-tree node: a tag plus the tags it directly implies."""

    tag: TagResponse
    consequents: list[TagResponse]


class TagListResponse(BaseModel):
    """Success envelope for `GET /api/tags`: {data, meta}."""

    data: list[TagResponse]
    meta: dict[str, Any] = Field(default_factory=dict)


class TagTreeResponse(BaseModel):
    """Success envelope for `GET /api/tags/tree`."""

    data: list[TagTreeNode]
    meta: dict[str, Any] = Field(default_factory=dict)
