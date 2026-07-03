"""Post editing: full-replacement tag update, delete (cascade + files), next.

Reuses ``tags.tag_post`` for the add side of a tag-set replacement (so the
implication closure is materialized per ADR-0001). The remove side — deleting
``post_tags`` rows and decrementing ``post_count`` — lives here because slice
2's tag service is add-only by design (the ADR's sticky-delete rule concerns
implications, not per-post tag membership). Deleting a post_tags row never
retracts an implication: it just removes that tag from that one post, leaving
other posts and the implication graph untouched.
"""
from __future__ import annotations

import shutil
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.models.post import Post
from app.models.tag import PostTag, Tag
from app.services import search, tags
from app.services.errors import NotFoundError


def update_post(
    db: Session,
    post_id: int,
    *,
    tag_names: list[str] | None = None,
    rating: str | None = None,
) -> Post:
    """Full-replace the post's tag set and/or change its rating.

    ``tag_names`` (when not None) becomes the exact new tag set: existing tags
    not in the list are removed (post_tags row deleted, post_count -1), new
    ones are added via ``tags.tag_post`` (which materializes the implication
    closure and bumps post_count). ``rating`` (when not None) overwrites.
    Either field may be omitted to leave it untouched.
    """
    post = search.get_post(db, post_id)  # 404
    if rating is not None:
        post.rating = rating

    if tag_names is not None:
        # Current tag ids + names on this post.
        current_rows = db.execute(
            select(PostTag.tag_id).where(PostTag.post_id == post_id)
        ).all()
        current_ids = {tid for (tid,) in current_rows}

        # Resolve target names to tags (get-or-create), collecting (id, name).
        target: list[tuple[int, str]] = []
        for name in tag_names:
            n = name.strip()
            if not n:
                continue
            t = db.execute(select(Tag).where(Tag.name == n)).scalar_one_or_none()
            if t is None:
                t = Tag(name=n, category="general", post_count=0)
                db.add(t)
                db.flush()
            target.append((t.id, n))
        target_ids = {tid for tid, _ in target}

        # Add: target - current → tag_post materializes the closure.
        to_add = [n for tid, n in target if tid not in current_ids]
        if to_add:
            tags.tag_post(db, post_id, to_add)

        # Remove: current - target → delete post_tags rows + post_count -1.
        # Re-fetch current after tag_post may have added new rows.
        current_after_add = {
            tid for (tid,) in db.execute(
                select(PostTag.tag_id).where(PostTag.post_id == post_id)
            ).all()
        }
        to_remove = current_after_add - target_ids
        for tid in to_remove:
            row = db.execute(
                select(PostTag).where(
                    PostTag.post_id == post_id, PostTag.tag_id == tid
                )
            ).scalar_one_or_none()
            if row is not None:
                db.delete(row)
                t = db.get(Tag, tid)
                if t is not None and t.post_count > 0:
                    t.post_count -= 1

    db.add(post)
    db.commit()
    db.refresh(post)
    return post


def delete_post(db: Session, post_id: int) -> None:
    """Delete a post: remove its media directory, then the DB row (cascade
    handles post_tags / favorite_items). 404 if it doesn't exist.

    Files are removed before the DB row: if file deletion fails, the post
    still exists and the caller can retry. The reverse (DB row gone, files
    lingering) leaves orphan files pointing at nothing, which is worse.
    """
    post = search.get_post(db, post_id)  # 404

    post_dir = settings.media_path / "posts" / str(post_id)
    if post_dir.exists():
        shutil.rmtree(post_dir)

    db.delete(post)
    db.commit()


def next_post(db: Session, post_id: int) -> tuple[int | None, int | None]:
    """Return ``(prev_id, next_id)`` for detail-page keyboard navigation.

    Computed over the global id-desc view (newest first), excluding duplicates
    (``duplicate_of_id IS NOT NULL``) to match the gallery main view. Not
    filtered by tags/safe_mode — the detail page navigates the whole gallery,
    not a search result set.
    """
    search.get_post(db, post_id)  # 404 if the post itself doesn't exist

    # "next" in id-desc view = the next newer-ingested post = smaller id.
    next_id = db.execute(
        select(Post.id)
        .where(Post.id < post_id, Post.duplicate_of_id.is_(None))
        .order_by(Post.id.desc())
        .limit(1)
    ).scalar_one_or_none()

    # "prev" in id-desc view = the previous (larger id).
    prev_id = db.execute(
        select(Post.id)
        .where(Post.id > post_id, Post.duplicate_of_id.is_(None))
        .order_by(Post.id.asc())
        .limit(1)
    ).scalar_one_or_none()

    return prev_id, next_id
