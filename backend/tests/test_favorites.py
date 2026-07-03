"""Favorites (collections) — F7 endpoints + star toggle (slice 8 backend part).

Covers AC1-AC7. Uses ``media.ingest`` to create real posts, then exercises the
collection CRUD, add/remove/reorder, and the star toggle end to end.
"""
from __future__ import annotations

import io
from pathlib import Path

import pytest
from PIL import Image
from sqlalchemy import select
from fastapi.testclient import TestClient

from app import db as db_module
from app.config import settings
from app.models.favorite import Favorite, FavoriteItem
from app.services import favorites, media


# --- fixtures --------------------------------------------------------------

@pytest.fixture()
def media_dir(tmp_path, monkeypatch) -> Path:
    d = tmp_path / "media"
    d.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(settings, "media_dir", str(d))
    return settings.media_path


@pytest.fixture()
def db():
    s = db_module.SessionLocal()
    try:
        yield s
    finally:
        s.close()


def _setup(client: TestClient) -> None:
    client.post("/api/auth/setup", json={"username": "admin", "password": "pw12345678"})


def _png_bytes(w: int, h: int, rgb: tuple[int, int, int]) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (w, h), rgb).save(buf, format="PNG")
    return buf.getvalue()


def _ingest_post(db, media_dir: Path, rgb: tuple[int, int, int]) -> int:
    return media.ingest(
        db, _png_bytes(100, 100, rgb),
        source_site="local", source_id=None, source_url=None,
        file_ext="png", is_animated=False,
    ).id


# --- AC1: collection CRUD --------------------------------------------------

def test_favorites_crud(client: TestClient, media_dir: Path, db) -> None:
    """AC1: create / list (compact, no posts) / detail (with items). 401 when
    unauthenticated."""
    # 401 on every endpoint without a cookie.
    for method, path, kwargs in (
        ("get", "/api/favorites", {}),
        ("post", "/api/favorites", {"json": {"name": "x"}}),
        ("get", "/api/favorites/1", {}),
    ):
        r = getattr(client, method)(path, **kwargs)
        assert r.status_code == 401, f"{method.upper()} {path} needs auth, got {r.status_code}"

    _setup(client)
    r = client.post("/api/favorites", json={"name": "my collection"})
    assert r.status_code == 201, r.text
    fav_id = r.json()["id"]
    assert r.json()["item_count"] == 0

    # List is compact — no items key, just item_count.
    r = client.get("/api/favorites")
    assert r.status_code == 200
    assert any(f["name"] == "my collection" for f in r.json())
    assert "items" not in r.json()[0]

    # Detail has items (empty so far).
    r = client.get(f"/api/favorites/{fav_id}")
    assert r.status_code == 200
    assert r.json()["items"] == []

    # Detail of a missing collection → 404.
    r = client.get("/api/favorites/999999")
    assert r.status_code == 404


# --- AC2: add / remove item ------------------------------------------------

def test_add_remove_item(client: TestClient, media_dir: Path, db) -> None:
    """AC2: add a post (tail position), remove it; re-adding the same post is
    409 (composite-PK dedup)."""
    _setup(client)
    pid = _ingest_post(db, media_dir, (1, 2, 3))
    r = client.post("/api/favorites", json={"name": "c"})
    fav_id = r.json()["id"]

    # Add — position 0.
    r = client.post(f"/api/favorites/{fav_id}/items", params={"post_id": pid})
    assert r.status_code == 201
    assert r.json()["position"] == 0

    # Add a second post — position 1 (tail).
    pid2 = _ingest_post(db, media_dir, (4, 5, 6))
    r = client.post(f"/api/favorites/{fav_id}/items", params={"post_id": pid2})
    assert r.json()["position"] == 1

    # Re-add the first post → 409.
    r = client.post(f"/api/favorites/{fav_id}/items", params={"post_id": pid})
    assert r.status_code == 409

    # Remove the first.
    r = client.delete(f"/api/favorites/{fav_id}/items/{pid}")
    assert r.status_code == 204
    detail = client.get(f"/api/favorites/{fav_id}").json()
    assert [i["post_id"] for i in detail["items"]] == [pid2]

    # Remove a non-member → 404.
    r = client.delete(f"/api/favorites/{fav_id}/items/{pid}")
    assert r.status_code == 404


# --- AC3: reorder ----------------------------------------------------------

def test_reorder_item(client: TestClient, media_dir: Path, db) -> None:
    """AC3: PATCH sets a member's position."""
    _setup(client)
    p1 = _ingest_post(db, media_dir, (1, 1, 1))
    p2 = _ingest_post(db, media_dir, (2, 2, 2))
    fav_id = client.post("/api/favorites", json={"name": "r"}).json()["id"]
    client.post(f"/api/favorites/{fav_id}/items", params={"post_id": p1})
    client.post(f"/api/favorites/{fav_id}/items", params={"post_id": p2})

    # Swap positions: p1 (was 0) → 1, p2 (was 1) → 0. Avoid same-position ties
    # so the resulting order is deterministic.
    client.patch(f"/api/favorites/{fav_id}/items/{p1}", json={"position": 1})
    r = client.patch(f"/api/favorites/{fav_id}/items/{p2}", json={"position": 0})
    assert r.status_code == 200
    assert r.json()["position"] == 0

    items = client.get(f"/api/favorites/{fav_id}").json()["items"]
    assert items[0]["post_id"] == p2
    assert items[1]["post_id"] == p1


# --- AC4 + AC5: star toggle + default-independence -------------------------

def test_star_toggle_and_default_independence(client: TestClient, media_dir: Path, db) -> None:
    """AC4: star toggles default-collection membership (and lazily creates it).
    AC5: a post can be in the default (starred) and a named collection at once."""
    _setup(client)
    pid = _ingest_post(db, media_dir, (9, 8, 7))

    # No default collection exists yet.
    assert db.execute(select(Favorite).where(Favorite.name == favorites.DEFAULT_FAVORITE_NAME)).first() is None

    # Star → favorited=True, default collection lazily created.
    r = client.post(f"/api/posts/{pid}/favorite")
    assert r.status_code == 200
    assert r.json()["favorited"] is True
    default = db.execute(select(Favorite).where(Favorite.name == favorites.DEFAULT_FAVORITE_NAME)).scalar_one()
    assert default is not None

    # The post is a member of the default collection.
    members = {row.post_id for row in db.execute(select(FavoriteItem).where(FavoriteItem.favorite_id == default.id)).scalars()}
    assert pid in members

    # Add the same post to a named collection — independent of the star.
    named_id = client.post("/api/favorites", json={"name": "named"}).json()["id"]
    r = client.post(f"/api/favorites/{named_id}/items", params={"post_id": pid})
    assert r.status_code == 201

    # Post is now in BOTH default (starred) and named.
    named_members = {row.post_id for row in db.execute(select(FavoriteItem).where(FavoriteItem.favorite_id == named_id)).scalars()}
    assert pid in named_members and pid in members, "post should be in both"

    # Unstar — removes from default only, named membership survives.
    r = client.post(f"/api/posts/{pid}/favorite")
    assert r.json()["favorited"] is False
    default_members_after = {row.post_id for row in db.execute(select(FavoriteItem).where(FavoriteItem.favorite_id == default.id)).scalars()}
    assert pid not in default_members_after
    named_members_after = {row.post_id for row in db.execute(select(FavoriteItem).where(FavoriteItem.favorite_id == named_id)).scalars()}
    assert pid in named_members_after, "named membership must survive unstar"


# --- AC6: no fav_count -----------------------------------------------------

def test_no_fav_count_in_responses(client: TestClient, media_dir: Path, db) -> None:
    """AC6: no favorite-count field appears anywhere — favorited state is
    membership only (grilling decision)."""
    _setup(client)
    pid = _ingest_post(db, media_dir, (1, 1, 1))
    client.post(f"/api/posts/{pid}/favorite")  # star it

    # The post list/detail responses carry no fav_count / favorite_count.
    r = client.get("/api/posts")
    assert "fav_count" not in r.json()["data"][0]
    assert "favorite_count" not in r.json()["data"][0]
    r = client.get(f"/api/posts/{pid}")
    assert "fav_count" not in r.json()
    assert "favorite_count" not in r.json()

    # The favorites list/detail carry item_count (a collection's size), not a
    # per-post favorite count — and no fav_count field name.
    r = client.get("/api/favorites")
    for f in r.json():
        assert "fav_count" not in f
    # The star toggle response is just {favorited: bool}, no count.
    r = client.post(f"/api/posts/{pid}/favorite")
    assert set(r.json()) == {"favorited"}


# --- AC7: 404 on missing post / collection --------------------------------

def test_404_on_missing(client: TestClient, media_dir: Path, db) -> None:
    """AC7: adding to a missing collection is 404; adding a missing post is 404;
    starring a missing post is 404."""
    _setup(client)
    pid = _ingest_post(db, media_dir, (0, 0, 0))
    fav_id = client.post("/api/favorites", json={"name": "x"}).json()["id"]

    # Missing collection.
    r = client.post("/api/favorites/999999/items", params={"post_id": pid})
    assert r.status_code == 404

    # Missing post.
    r = client.post(f"/api/favorites/{fav_id}/items", params={"post_id": 999999})
    assert r.status_code == 404

    # Star a missing post.
    r = client.post("/api/posts/999999/favorite")
    assert r.status_code == 404
