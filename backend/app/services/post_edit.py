"""Post editing: full-replacement tag update, delete (cascade + files).

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
from sqlalchemy.exc import IntegrityError
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

    ``tag_names`` (when not None) becomes the new tag set: existing tags
    outside the target set's implication closure are removed (post_tags row
    deleted, post_count -1), new ones are added via ``tags.tag_post`` (which
    materializes the implication closure and bumps post_count). Consequents
    of the target tags are kept, per ADR-0001's "post_tags is always the
    expanded closure" invariant. ``rating`` (when not None) overwrites.
    Either field may be omitted to leave it untouched.

    The whole update is one transaction: a failure at any point rolls back
    both the rating change and the tag changes, so no add/remove middle state
    is ever committed. A lost tag get-or-create race (IntegrityError on the
    ``Tag.name`` unique constraint) reruns the pass once — the re-query then
    finds the concurrent winner's row.
    """
    post = search.get_post(db, post_id)  # 404

    for attempt in range(2):
        try:
            _apply_changes(db, post, tag_names=tag_names, rating=rating)
            db.commit()
            break
        except IntegrityError:
            db.rollback()
            if attempt == 1:
                raise
        except Exception:
            db.rollback()
            raise
    db.refresh(post)
    return post


def _apply_changes(
    db: Session,
    post: Post,
    *,
    tag_names: list[str] | None,
    rating: str | None,
) -> None:
    """One flush-only pass of ``update_post``'s mutations.

    Commit/rollback is the caller's job, so a lost get-or-create race can
    discard and rerun the pass as a unit (the rollback also reverts the
    rating change and any tags created earlier in the pass).
    """
    post_id = post.id
    if rating is not None:
        post.rating = rating

    if tag_names is not None:
        # Current tag ids on this post.
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

        # Add: target - current → tag_post materializes the closure
        # (flush-only; this pass's caller owns the single commit).
        to_add = [n for tid, n in target if tid not in current_ids]
        if to_add:
            tags.tag_post(db, post_id, to_add, commit=False)

        # Remove: current - closure(target) → delete post_tags rows +
        # post_count -1. Comparing against the closure (not the bare target
        # set) keeps the implication consequents tag_post just materialized —
        # post_tags must stay the fully-expanded set (ADR-0001).
        current_after_add = {
            tid for (tid,) in db.execute(
                select(PostTag.tag_id).where(PostTag.post_id == post_id)
            ).all()
        }
        to_remove = current_after_add - tags.closure_of(db, list(target_ids))
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


def delete_post(db: Session, post_id: int) -> None:
    """Delete a post: remove its media directory, then the DB row (cascade
    handles post_tags / favorite_items). 404 if it doesn't exist.

    Files are removed before the DB row: if file deletion fails, the post
    still exists and the caller can retry. The reverse (DB row gone, files
    lingering) leaves orphan files pointing at nothing, which is worse.

    The FK CASCADE deletes the post_tags rows behind the ORM's back, so each
    tag's denormalized post_count is decremented here first (clamped at 0) to
    keep the "post_count equals the number of post_tags rows" invariant.
    """
    post = search.get_post(db, post_id)  # 404

    post_dir = settings.media_path / "posts" / str(post_id)
    if post_dir.exists():
        shutil.rmtree(post_dir)

    tag_ids = db.execute(
        select(PostTag.tag_id).where(PostTag.post_id == post_id)
    ).scalars().all()
    for tid in tag_ids:
        t = db.get(Tag, tid)
        if t is not None and t.post_count > 0:
            t.post_count -= 1

    db.delete(post)
    db.commit()
