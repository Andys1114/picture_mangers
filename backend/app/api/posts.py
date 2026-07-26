"""Posts routes: list (browse) + single detail.

Thin handlers delegating to app.services.search. List returns the success
envelope {data, meta}; detail returns the full post with its expanded tag set.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_current_session, get_current_user
from app.models.user import Session as SessionRow
from app.models.user import User
from app.schemas.favorite import StarToggleResponse
from app.schemas.post import (
    PostDetailResponse,
    PostListResponse,
    PostNextResponse,
    PostSummaryResponse,
    PostUpdateRequest,
    TagResponse,
)
from app.services import favorites, post_edit, search

router = APIRouter(prefix="/posts", tags=["posts"])


def _summary(post, favorite: bool) -> PostSummaryResponse:  # type: ignore[no-untyped-def]
    return PostSummaryResponse(
        id=post.id,
        preview_path=post.preview_path,
        width=post.width,
        height=post.height,
        rating=post.rating,
        is_animated=post.is_animated,
        favorite=favorite,
    )


def _detail(post, tag_rows, favorite: bool) -> PostDetailResponse:  # type: ignore[no-untyped-def]
    return PostDetailResponse(
        id=post.id,
        preview_path=post.preview_path,
        width=post.width,
        height=post.height,
        rating=post.rating,
        is_animated=post.is_animated,
        favorite=favorite,
        file_path=post.file_path,
        thumb_path=post.thumb_path,
        source_site=post.source_site,
        source_url=post.source_url,
        md5=post.md5,
        created_at=post.created_at,
        tags=[
            TagResponse(
                id=t.id,
                name=t.name,
                category=t.category,
                post_count=t.post_count,
                is_deprecated=t.is_deprecated,
            )
            for t in tag_rows
        ],
    )


@router.get("", response_model=PostListResponse)
def list_posts(
    tags: str = Query("", description="Space-separated tag names, AND-matched over post_tags"),
    page: int = Query(1, ge=1),
    limit: int = Query(40, ge=1, le=200),
    order: str = Query("id", pattern="^(id|random)$"),
    ratings: str = Query(
        "",
        pattern="^$|^(safe|questionable|explicit)(,(safe|questionable|explicit))*$",
        description="Comma-separated rating filter; ignored while safe mode is on",
    ),
    session: SessionRow = Depends(get_current_session),
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
        ratings=[r for r in ratings.split(",") if r] or None,
    )
    # favorite = default-collection membership, fetched with one IN query.
    starred = favorites.favorite_post_ids(db, [p.id for p in rows])
    return PostListResponse(
        data=[_summary(p, favorite=p.id in starred) for p in rows],
        meta={"page": page, "total": total},
    )


@router.get("/{post_id}", response_model=PostDetailResponse)
def get_post(
    post_id: int,
    session: SessionRow = Depends(get_current_session),
    db: Session = Depends(get_db),
) -> PostDetailResponse:
    """Single post detail with its expanded tag set.

    Safe mode applies here too: a non-safe post 404s while the session has
    safe_mode on (same server-side injection as the list view).
    """
    post = search.get_post(db, post_id, safe_mode=session.safe_mode)
    tag_rows = search.tags_for_post(db, post_id)
    favorite = post_id in favorites.favorite_post_ids(db, [post_id])
    return _detail(post, tag_rows, favorite)


@router.post("/{post_id}/favorite", response_model=StarToggleResponse)
def toggle_favorite(
    post_id: int,
    _user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> StarToggleResponse:
    """Star/unstar a post — toggle its membership in the default collection.

    Returns the new state so the client can sync the button without a re-fetch.
    """
    favorited = favorites.toggle_star(db, post_id)
    return StarToggleResponse(favorited=favorited)


@router.get("/{post_id}/next", response_model=PostNextResponse)
def get_next(
    post_id: int,
    session: SessionRow = Depends(get_current_session),
    db: Session = Depends(get_db),
) -> PostNextResponse:
    """Prev/next post ids for detail-page keyboard navigation (id-desc view,
    safe-mode-filtered like the gallery)."""
    prev_id, next_id = search.next_post(db, post_id, safe_mode=session.safe_mode)
    return PostNextResponse(prev_id=prev_id, next_id=next_id)


@router.patch("/{post_id}", response_model=PostDetailResponse)
def update_post(
    post_id: int,
    payload: PostUpdateRequest,
    _user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PostDetailResponse:
    """Edit a post — full-replace tags (when provided) and/or change rating."""
    post = post_edit.update_post(db, post_id, tag_names=payload.tags, rating=payload.rating)
    tag_rows = search.tags_for_post(db, post_id)
    favorite = post_id in favorites.favorite_post_ids(db, [post_id])
    return _detail(post, tag_rows, favorite)


@router.delete("/{post_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_post(
    post_id: int,
    _user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    """Delete a post — removes its media directory and DB row (cascade)."""
    post_edit.delete_post(db, post_id)
