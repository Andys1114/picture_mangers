"""Favorite (collection) routes: list, create, detail, add/remove/reorder items.

Thin handlers delegating to app.services.favorites. All require auth.
Starring a post (the default-collection toggle) is exposed on the post resource
itself — see app.api.posts — since "star this post" is a post action, not a
collection action, from the client's perspective.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_current_user
from app.models.user import User
from app.schemas.favorite import (
    FavoriteCreateRequest,
    FavoriteDetailResponse,
    FavoriteItemReorderRequest,
    FavoriteItemResponse,
    FavoriteResponse,
)
from app.services import favorites

router = APIRouter(prefix="/favorites", tags=["favorites"])


def _to_response(fav, item_count: int) -> FavoriteResponse:  # type: ignore[no-untyped-def]
    return FavoriteResponse(id=fav.id, name=fav.name, item_count=item_count)


@router.get("", response_model=list[FavoriteResponse])
def list_favorites(
    _user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[FavoriteResponse]:
    """List all collections (compact — item_count, no posts)."""
    return [_to_response(fav, count) for fav, count in favorites.list_favorites(db)]


@router.post("", response_model=FavoriteResponse, status_code=status.HTTP_201_CREATED)
def create_favorite(
    payload: FavoriteCreateRequest,
    _user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> FavoriteResponse:
    """Create a named collection."""
    fav = favorites.create_favorite(db, payload.name)
    return _to_response(fav, 0)


@router.get("/{favorite_id}", response_model=FavoriteDetailResponse)
def get_favorite(
    favorite_id: int,
    _user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> FavoriteDetailResponse:
    """Collection detail — includes member posts ordered by position."""
    fav = favorites.get_favorite(db, favorite_id)
    items = favorites.list_items(db, favorite_id)
    return FavoriteDetailResponse(
        id=fav.id,
        name=fav.name,
        items=[FavoriteItemResponse(post_id=i.post_id, position=i.position) for i in items],
    )


@router.post("/{favorite_id}/items", response_model=FavoriteItemResponse, status_code=status.HTTP_201_CREATED)
def add_item(
    favorite_id: int,
    post_id: int,
    _user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> FavoriteItemResponse:
    """Add a post to a collection at the tail position."""
    item = favorites.add_item(db, favorite_id, post_id)
    return FavoriteItemResponse(post_id=item.post_id, position=item.position)


@router.delete("/{favorite_id}/items/{post_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_item(
    favorite_id: int,
    post_id: int,
    _user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    """Remove a post from a collection."""
    favorites.remove_item(db, favorite_id, post_id)


@router.patch("/{favorite_id}/items/{post_id}", response_model=FavoriteItemResponse)
def reorder_item(
    favorite_id: int,
    post_id: int,
    payload: FavoriteItemReorderRequest,
    _user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> FavoriteItemResponse:
    """Set a member's position."""
    item = favorites.reorder_item(db, favorite_id, post_id, payload.position)
    return FavoriteItemResponse(post_id=item.post_id, position=item.position)
