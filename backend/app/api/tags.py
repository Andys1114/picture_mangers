"""Tag resource routes: list, tree, detail, create, update.

Thin handlers delegating to app.services.tags. All require auth. This slice
exposes tag-resource CRUD only — implication creation and post-tagging are
service functions (no HTTP endpoint) consumed by the scraper (slice 4) and the
future edit endpoint (slice 6).
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_current_user
from app.models.user import User
from app.schemas.tag import (
    TagCreateRequest,
    TagListResponse,
    TagResponse,
    TagTreeNode,
    TagTreeResponse,
    TagUpdateRequest,
)
from app.services import tags

router = APIRouter(prefix="/tags", tags=["tags"])


def _to_response(tag) -> TagResponse:  # type: ignore[no-untyped-def]
    return TagResponse(
        id=tag.id,
        name=tag.name,
        category=tag.category,
        post_count=tag.post_count,
        is_deprecated=tag.is_deprecated,
    )


@router.get("", response_model=TagListResponse)
def list_tags(
    search: str = Query("", description="Substring match on name (case-insensitive)"),
    category: str | None = Query(None, description="Filter by category"),
    order: str = Query("count", pattern="^(count|name)$"),
    _user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> TagListResponse:
    """Tag list for the /tags page + autocomplete."""
    rows = tags.list_tags(db, search=search, category=category, order=order)
    return TagListResponse(data=[_to_response(t) for t in rows])


@router.get("/tree", response_model=TagTreeResponse)
def get_tree(
    _user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> TagTreeResponse:
    """Implication tree: each antecedent with its direct consequents."""
    rows = tags.tag_tree(db)
    return TagTreeResponse(
        data=[
            TagTreeNode(tag=_to_response(ant), consequents=[_to_response(c) for c in cons])
            for ant, cons in rows
        ]
    )


@router.get("/{tag_id}", response_model=TagResponse)
def get_tag(
    tag_id: int,
    _user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> TagResponse:
    """Single tag detail."""
    return _to_response(tags.get_tag(db, tag_id))


@router.post("", response_model=TagResponse, status_code=status.HTTP_201_CREATED)
def create_tag(
    payload: TagCreateRequest,
    _user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> TagResponse:
    """Create a new tag. Conflict (409) if the name is taken."""
    return _to_response(tags.create_tag(db, payload.name, payload.category))


@router.patch("/{tag_id}", response_model=TagResponse)
def update_tag(
    tag_id: int,
    payload: TagUpdateRequest,
    _user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> TagResponse:
    """Rename and/or recategorize a tag. Conflict (409) on name collision."""
    return _to_response(tags.update_tag(db, tag_id, name=payload.name, category=payload.category))
