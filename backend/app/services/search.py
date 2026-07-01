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
) -> tuple[list[Post], int]:
    """Return (rows, total) for the gallery main view.

    - Duplicates (``duplicate_of_id IS NOT NULL``) are hidden by default.
    - ``safe_mode`` True forces ``rating='safe'`` (server-side injection).
    - ``tags`` is a list of tag names ANDed over ``post_tags``. Because
      implications are materialized at write time, this plain AND already
      hits the expanded tag set (searching ``miku`` matches ``vocaloid``
      posts because their ``post_tags`` already contain ``vocaloid``).
    - Default sort is ``id`` descending (newest first); ``random`` shuffles.
    """
    stmt = select(Post).where(Post.duplicate_of_id.is_(None))

    if safe_mode:
        stmt = stmt.where(Post.rating == "safe")

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


def get_post(db: Session, post_id: int) -> Post:
    """Return a single post (any rating/duplicate state) or raise 404."""
    post = db.get(Post, post_id)
    if post is None:
        raise NotFoundError("图片不存在")
    return post


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
