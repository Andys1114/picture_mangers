"""Post search / lookup service.

Search is AND-only over the materialized ``post_tags`` set this milestone
(see ADR-0001: implications are expanded at write time, so reads never
recurse). Rating + duplicate filters are layered on top of the tag query.
Safe mode is server-authoritative and injected here from the session.
"""
from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.post import Post
from app.models.tag import PostTag, Tag
from app.services.errors import NotFoundError


def list_posts(
    db: Session,
    *,
    tags: list[str],
    safe_mode: bool,
    page: int,
    limit: int,
    order: str = "id",
    ratings: list[str] | None = None,
) -> tuple[list[Post], int]:
    """Return (rows, total) for the gallery main view.

    - Duplicates (``duplicate_of_id IS NOT NULL``) are hidden by default.
    - ``safe_mode`` True forces ``rating='safe'`` (server-side injection);
      the ``ratings`` parameter is ignored entirely while it is on.
    - ``ratings`` (safe mode off only) restricts results to the given rating
      subset; ``None``/empty means no rating filter (all ratings).
    - ``tags`` is a list of tag names ANDed over ``post_tags``. Because
      implications are materialized at write time, this plain AND already
      hits the expanded tag set (searching ``miku`` matches ``vocaloid``
      posts because their ``post_tags`` already contain ``vocaloid``).
    - Default sort is ``id`` descending (newest first); ``random`` shuffles.
    """
    stmt = select(Post).where(Post.duplicate_of_id.is_(None))

    if safe_mode:
        stmt = stmt.where(Post.rating == "safe")
    elif ratings:
        stmt = stmt.where(Post.rating.in_(ratings))

    for name in tags:
        name = name.strip()
        if not name:
            continue
        stmt = stmt.where(
            Post.id.in_(
                select(PostTag.post_id)
                .join(Tag, PostTag.tag_id == Tag.id)
                .where(Tag.name == name)
            )
        )

    if order == "random":
        stmt = stmt.order_by(func.random())
    else:
        stmt = stmt.order_by(Post.id.desc())

    total = db.execute(select(func.count()).select_from(stmt.subquery())).scalar_one()
    rows = (
        db.execute(stmt.offset((page - 1) * limit).limit(limit))
        .scalars()
        .all()
    )
    return rows, total


def get_post(db: Session, post_id: int, *, safe_mode: bool = False) -> Post:
    """Return a single post or raise 404.

    ``safe_mode`` True also 404s non-safe posts, extending the server-side
    rating injection to the detail read path (a hidden post is
    indistinguishable from a missing one). Duplicate state is never filtered
    here — duplicates stay reachable by id.
    """
    post = db.get(Post, post_id)
    if post is None:
        raise NotFoundError("图片不存在")
    if safe_mode and post.rating != "safe":
        raise NotFoundError("图片不存在")
    return post


def next_post(
    db: Session, post_id: int, *, safe_mode: bool = False
) -> tuple[int | None, int | None]:
    """Return ``(prev_id, next_id)`` for detail-page keyboard navigation.

    Computed over the global id-desc view (newest first), excluding duplicates
    to match the gallery main view. Not filtered by tags — the detail page
    navigates the whole gallery, not a search result set — but ``safe_mode``
    True skips non-safe posts so navigation never lands on a hidden post.
    """
    get_post(db, post_id, safe_mode=safe_mode)  # 404 if missing or hidden

    # "next" = the next row down the newest-first list = smaller id.
    next_stmt = (
        select(Post.id)
        .where(Post.id < post_id, Post.duplicate_of_id.is_(None))
        .order_by(Post.id.desc())
        .limit(1)
    )
    # "prev" = the previous row (larger id).
    prev_stmt = (
        select(Post.id)
        .where(Post.id > post_id, Post.duplicate_of_id.is_(None))
        .order_by(Post.id.asc())
        .limit(1)
    )
    if safe_mode:
        next_stmt = next_stmt.where(Post.rating == "safe")
        prev_stmt = prev_stmt.where(Post.rating == "safe")

    next_id = db.execute(next_stmt).scalar_one_or_none()
    prev_id = db.execute(prev_stmt).scalar_one_or_none()
    return prev_id, next_id


def tags_for_post(db: Session, post_id: int) -> list[Tag]:
    """Return the expanded tag set for a post (the materialized post_tags rows)."""
    return (
        db.execute(
            select(Tag)
            .join(PostTag, PostTag.tag_id == Tag.id)
            .where(PostTag.post_id == post_id)
            .order_by(Tag.category, Tag.name)
        )
        .scalars()
        .all()
    )
