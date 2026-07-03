"""Post edit/delete/next endpoints (slice 6 backend).

Covers AC1-AC6. Uses ``media.ingest`` + ``tags.tag_post`` to set up posts with
tags, then exercises PATCH (full-replace tags / rating), DELETE (cascade +
files), and next (id-desc navigation).
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
from app.models.favorite import FavoriteItem
from app.models.post import Post
from app.models.tag import PostTag, Tag
from app.services import favorites, media, tags


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


def _ingest(db, media_dir: Path, rgb: tuple[int, int, int]) -> int:
    return media.ingest(
        db, _png_bytes(100, 100, rgb),
        source_site="local", source_id=None, source_url=None,
        file_ext="png", is_animated=False,
    ).id


def _tag_names_for_post(db, post_id: int) -> set[str]:
    rows = db.execute(
        select(Tag.name)
        .join(PostTag, PostTag.tag_id == Tag.id)
        .where(PostTag.post_id == post_id)
    ).scalars().all()
    return set(rows)


# --- AC1: full-replace tags ------------------------------------------------

def test_update_post_replace_tags(client: TestClient, media_dir: Path, db) -> None:
    """AC1: post tagged {a,b} → PATCH {tags:[b,c]} → post_tags = {b,c};
    post_count for a drops by 1, c rises by 1."""
    _setup(client)
    pid = _ingest(db, media_dir, (1, 2, 3))
    tags.tag_post(db, pid, ["a", "b"])
    assert _tag_names_for_post(db, pid) == {"a", "b"}

    r = client.patch(f"/api/posts/{pid}", json={"tags": ["b", "c"]})
    assert r.status_code == 200, r.text
    assert _tag_names_for_post(db, pid) == {"b", "c"}, "tags fully replaced"

    # post_count: a was 1 → 0 (or stays 0 if other posts), c 0 → 1.
    a = db.execute(select(Tag).where(Tag.name == "a")).scalar_one()
    assert a.post_count == 0
    c = db.execute(select(Tag).where(Tag.name == "c")).scalar_one()
    assert c.post_count == 1
    b = db.execute(select(Tag).where(Tag.name == "b")).scalar_one()
    assert b.post_count == 1, "b stayed at 1 (kept)"


# --- AC2 + AC3: rating / partial update ------------------------------------

def test_update_post_rating_and_partial(client: TestClient, media_dir: Path, db) -> None:
    """AC2: PATCH {rating} changes rating; AC3: omitting tags leaves them."""
    _setup(client)
    pid = _ingest(db, media_dir, (4, 5, 6))
    tags.tag_post(db, pid, ["keepme"])

    # Only rating — tags untouched.
    r = client.patch(f"/api/posts/{pid}", json={"rating": "explicit"})
    assert r.status_code == 200
    assert r.json()["rating"] == "explicit"
    assert _tag_names_for_post(db, pid) == {"keepme"}, "tags unchanged when omitted"

    # Only tags — rating untouched.
    r = client.patch(f"/api/posts/{pid}", json={"tags": ["newonly"]})
    assert r.status_code == 200
    assert r.json()["rating"] == "explicit", "rating unchanged when omitted"
    assert _tag_names_for_post(db, pid) == {"newonly"}


# --- AC4: delete cascade + files -------------------------------------------

def test_delete_post_cascade_and_files(client: TestClient, media_dir: Path, db) -> None:
    """AC4: delete removes the post row, cascades post_tags/favorite_items, and
    wipes the media/posts/{id}/ directory. 404 on a missing post."""
    _setup(client)
    pid = _ingest(db, media_dir, (7, 8, 9))
    tags.tag_post(db, pid, ["todelete"])
    favorites.toggle_star(db, pid)  # add to default → favorite_items row

    post_dir = settings.media_path / "posts" / str(pid)
    assert post_dir.exists()
    assert db.execute(select(PostTag).where(PostTag.post_id == pid)).first() is not None
    assert db.execute(select(FavoriteItem).where(FavoriteItem.post_id == pid)).first() is not None

    r = client.delete(f"/api/posts/{pid}")
    assert r.status_code == 204

    # Row gone.
    assert db.get(Post, pid) is None
    # Cascade: post_tags + favorite_items gone.
    assert db.execute(select(PostTag).where(PostTag.post_id == pid)).first() is None
    assert db.execute(select(FavoriteItem).where(FavoriteItem.post_id == pid)).first() is None
    # Files gone.
    assert not post_dir.exists()

    # 404 on missing.
    r = client.delete(f"/api/posts/{pid}")
    assert r.status_code == 404


# --- AC5: next --------------------------------------------------------------

def test_next_post(client: TestClient, media_dir: Path, db) -> None:
    """AC5: GET /api/posts/{id}/next returns {prev_id, next_id} over the id-desc
    view; head/tail yield null on the missing side."""
    _setup(client)
    # Three posts: ids 1, 2, 3 (ingest order). id-desc view: 3, 2, 1.
    p1 = _ingest(db, media_dir, (1, 1, 1))
    p2 = _ingest(db, media_dir, (2, 2, 2))
    p3 = _ingest(db, media_dir, (3, 3, 3))

    # Middle: prev = 3 (larger id), next = 1 (smaller id).
    r = client.get(f"/api/posts/{p2}/next")
    assert r.status_code == 200
    assert r.json() == {"prev_id": p3, "next_id": p1}

    # Head of id-desc (largest id = 3): prev null, next = 2.
    r = client.get(f"/api/posts/{p3}/next")
    assert r.json() == {"prev_id": None, "next_id": p2}

    # Tail (smallest id = 1): prev = 2, next null.
    r = client.get(f"/api/posts/{p1}/next")
    assert r.json() == {"prev_id": p2, "next_id": None}


# --- AC6: auth --------------------------------------------------------------

def test_edit_requires_auth(client: TestClient, media_dir: Path, db) -> None:
    """AC6: PATCH/DELETE/next all 401 without a cookie."""
    pid = _ingest(db, media_dir, (0, 0, 0))
    for method, path, kwargs in (
        ("patch", f"/api/posts/{pid}", {"json": {"rating": "safe"}}),
        ("delete", f"/api/posts/{pid}", {}),
        ("get", f"/api/posts/{pid}/next", {}),
    ):
        r = getattr(client, method)(path, **kwargs)
        assert r.status_code == 401, f"{method.upper()} {path} needs auth, got {r.status_code}"
