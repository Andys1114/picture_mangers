"""Favorite (collection) write/read service.

Implements the F7 semantics (parent PRD + CONTEXT.md):
- Multiple named collections ("playlists" of images), each with ordered posts.
- A single **default** collection carries the "star this post" action: starring
  = add/remove the post to/from the default collection. A post can live in the
  default collection and in named collections at the same time — they're
  independent.
- **No favorite counts**: whether a post is "favorited" is derived from
  ``favorite_items`` membership, never a counter on Post (grilling decision;
  see ``quality-guidelines.md``).

The default collection is **lazily created** on first star — there's no setup-
time hook and no ``is_default`` column (schema unchanged), so the default is
identified by a reserved name constant.
"""
from __future__ import annotations

from collections.abc import Iterable

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.favorite import Favorite, FavoriteItem
from app.services import search
from app.services.errors import ConflictError, NotFoundError

# Reserved name for the auto-maintained default (star) collection. The default
# is identified by this name (no schema flag column); names are unique, so a
# user-created collection with this exact name is simply reused by the star.
DEFAULT_FAVORITE_NAME = "默认收藏"


def get_favorite(db: Session, favorite_id: int) -> Favorite:
    """Return a collection by id or raise 404."""
    fav = db.get(Favorite, favorite_id)
    if fav is None:
        raise NotFoundError("收藏夹不存在")
    return fav


def list_favorites(db: Session) -> list[tuple[Favorite, int]]:
    """Return all collections with their item counts.

    Returns ``(Favorite, item_count)`` tuples so the API can build the
    list-response shape without a separate count query per row.
    """
    rows = db.execute(
        select(
            Favorite,
            func.count(FavoriteItem.post_id).label("item_count"),
        )
        .outerjoin(FavoriteItem, FavoriteItem.favorite_id == Favorite.id)
        .group_by(Favorite.id)
        .order_by(Favorite.id)
    ).all()
    return [(fav, count or 0) for fav, count in rows]


def create_favorite(db: Session, name: str) -> Favorite:
    """Create a named collection. 409 if the name is already taken.

    Names identify collections (the default is looked up by name), so
    duplicates are rejected here; the unique index on ``favorites.name`` is
    the DB-level backstop.
    """
    existing = db.execute(
        select(Favorite).where(Favorite.name == name)
    ).scalars().first()
    if existing is not None:
        raise ConflictError("收藏夹名称已存在")
    fav = Favorite(name=name)
    db.add(fav)
    db.commit()
    db.refresh(fav)
    return fav


def get_or_create_default(db: Session) -> Favorite:
    """Return the default (star) collection, lazily creating it.

    Reads with ``.first()`` on the oldest row: names are unique since the
    ``ux_favorites_name`` migration, but a legacy DB that predates it may
    still hold duplicates — the oldest one keeps the star role.
    """
    fav = (
        db.execute(
            select(Favorite)
            .where(Favorite.name == DEFAULT_FAVORITE_NAME)
            .order_by(Favorite.id)
        )
        .scalars()
        .first()
    )
    if fav is None:
        fav = Favorite(name=DEFAULT_FAVORITE_NAME)
        db.add(fav)
        db.commit()
        db.refresh(fav)
    return fav


def favorite_post_ids(db: Session, post_ids: Iterable[int]) -> set[int]:
    """Return the subset of ``post_ids`` that are in the default collection.

    Drives the ``favorite`` field on post responses: membership-derived, never
    a count. One IN query for a whole page of posts. Returns an empty set when
    the default collection doesn't exist yet (nothing has been starred).
    """
    ids = list(post_ids)
    if not ids:
        return set()
    default = (
        db.execute(
            select(Favorite)
            .where(Favorite.name == DEFAULT_FAVORITE_NAME)
            .order_by(Favorite.id)
        )
        .scalars()
        .first()
    )
    if default is None:
        return set()
    rows = db.execute(
        select(FavoriteItem.post_id).where(
            FavoriteItem.favorite_id == default.id,
            FavoriteItem.post_id.in_(ids),
        )
    ).all()
    return {post_id for (post_id,) in rows}


def list_items(db: Session, favorite_id: int) -> list[FavoriteItem]:
    """Return a collection's items ordered by position."""
    get_favorite(db, favorite_id)  # 404 if missing
    return list(
        db.execute(
            select(FavoriteItem)
            .where(FavoriteItem.favorite_id == favorite_id)
            .order_by(FavoriteItem.position)
        ).scalars().all()
    )


def _next_position(db: Session, favorite_id: int) -> int:
    """Return the next tail position for a collection (0 if empty)."""
    max_pos = db.execute(
        select(func.max(FavoriteItem.position)).where(FavoriteItem.favorite_id == favorite_id)
    ).scalar_one()
    # max() over no rows returns None; treat None and any int (incl. 0) correctly.
    return (max_pos if max_pos is not None else -1) + 1


def add_item(db: Session, favorite_id: int, post_id: int) -> FavoriteItem:
    """Add a post to a collection at the tail position.

    Raises 404 if the collection or post doesn't exist, 409 if the post is
    already a member (composite-PK dedup — idempotent reject, not silent).
    """
    get_favorite(db, favorite_id)  # 404
    search.get_post(db, post_id)   # 404 if post missing

    existing = db.execute(
        select(FavoriteItem).where(
            FavoriteItem.favorite_id == favorite_id,
            FavoriteItem.post_id == post_id,
        )
    ).scalar_one_or_none()
    if existing is not None:
        raise ConflictError("该图片已在收藏夹中")

    item = FavoriteItem(
        favorite_id=favorite_id,
        post_id=post_id,
        position=_next_position(db, favorite_id),
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def remove_item(db: Session, favorite_id: int, post_id: int) -> None:
    """Remove a post from a collection. 404 if not a member."""
    item = db.execute(
        select(FavoriteItem).where(
            FavoriteItem.favorite_id == favorite_id,
            FavoriteItem.post_id == post_id,
        )
    ).scalar_one_or_none()
    if item is None:
        raise NotFoundError("该图片不在收藏夹中")
    db.delete(item)
    db.commit()


def reorder_item(db: Session, favorite_id: int, post_id: int, position: int) -> FavoriteItem:
    """Set a member's position. Does not compact gaps (single-user scale)."""
    item = db.execute(
        select(FavoriteItem).where(
            FavoriteItem.favorite_id == favorite_id,
            FavoriteItem.post_id == post_id,
        )
    ).scalar_one_or_none()
    if item is None:
        raise NotFoundError("该图片不在收藏夹中")
    item.position = position
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def toggle_star(db: Session, post_id: int) -> bool:
    """Toggle a post's membership in the default (star) collection.

    Returns the new state: True if now starred (added), False if unstarred
    (removed). Lazily creates the default collection on first add. Validates
    the post exists (404).
    """
    search.get_post(db, post_id)  # 404 if post missing
    default = get_or_create_default(db)

    existing = db.execute(
        select(FavoriteItem).where(
            FavoriteItem.favorite_id == default.id,
            FavoriteItem.post_id == post_id,
        )
    ).scalar_one_or_none()
    if existing is not None:
        db.delete(existing)
        db.commit()
        return False
    item = FavoriteItem(
        favorite_id=default.id,
        post_id=post_id,
        position=_next_position(db, default.id),
    )
    db.add(item)
    db.commit()
    return True
