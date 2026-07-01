"""Posts routes: list (browse) + single detail.

Thin handlers delegating to app.services.search. List returns the success
envelope {data, meta}; detail returns the full post with its expanded tag set.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_current_session, get_current_user
from app.models.user import Session, User
from app.schemas.post import (
    PostDetailResponse,
    PostListResponse,
    PostSummaryResponse,
    TagResponse,
)
from app.services import search

router = APIRouter(prefix="/posts", tags=["posts"])


def _summary(post) -> PostSummaryResponse:  # type: ignore[no-untyped-def]
    return PostSummaryResponse(
        id=post.id,
        preview_path=post.preview_path,
        width=post.width,
        height=post.height,
        rating=post.rating,
        is_animated=post.is_animated,
        favorite=False,  # favorites API lands later; derived from membership, never a count
    )


@router.get("", response_model=PostListResponse)
def list_posts(
    tags: str = Query("", description="Space-separated tag names, AND-matched over post_tags"),
    page: int = Query(1, ge=1),
    limit: int = Query(40, ge=1, le=200),
    order: str = Query("id", pattern="^(id|random)$"),
    session: Session = Depends(get_current_session),
    db: Session = Depends(get_db),
) -> PostListResponse:
    """Gallery main view: paginated, safe-mode-filtered, duplicate-excluded."""
    rows, total = search.list_posts(
        db,
        tags=tags.split(),
        safe_mode=session.safe_mode,
        page=page,
        limit=limit,
        order=order,
    )
    return PostListResponse(
        data=[_summary(p) for p in rows],
        meta={"page": page, "total": total},
    )


@router.get("/{post_id}", response_model=PostDetailResponse)
def get_post(
    post_id: int,
    _user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PostDetailResponse:
    """Single post detail with its expanded tag set."""
    post = search.get_post(db, post_id)
    tag_rows = search.tags_for_post(db, post_id)
    return PostDetailResponse(
        id=post.id,
        preview_path=post.preview_path,
        width=post.width,
        height=post.height,
        rating=post.rating,
        is_animated=post.is_animated,
        favorite=False,
        file_path=post.file_path,
        thumb_path=post.thumb_path,
        source_site=post.source_site,
        source_url=post.source_url,
        md5=post.md5,
        created_at=post.created_at,
        tags=[
            TagResponse(id=t.id, name=t.name, category=t.category, post_count=t.post_count)
            for t in tag_rows
        ],
    )
