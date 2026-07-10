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
from app.services import favorites, media, post_edit, tags


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


# --- regression: implication closure survives full-replace -------------------

def test_update_post_replace_keeps_implication_closure(
    client: TestClient, media_dir: Path, db
) -> None:
    # audit #3: with miku→vocaloid, PATCH {tags:["miku"]} materializes
    # {miku, vocaloid}; the remove phase must not strip the consequent.
    _setup(client)
    pid = _ingest(db, media_dir, (11, 22, 33))
    miku = tags.create_tag(db, "miku", "character")
    voc = tags.create_tag(db, "vocaloid", "general")
    tags.create_implication(db, miku.id, voc.id)

    r = client.patch(f"/api/posts/{pid}", json={"tags": ["miku"]})
    assert r.status_code == 200, r.text
    assert _tag_names_for_post(db, pid) == {"miku", "vocaloid"}, (
        "materialized consequent must survive the replace"
    )
    db.expire_all()
    assert db.get(Tag, miku.id).post_count == 1
    assert db.get(Tag, voc.id).post_count == 1

    # Replacing away the antecedent removes the whole closure (and only then).
    r = client.patch(f"/api/posts/{pid}", json={"tags": ["plain"]})
    assert r.status_code == 200, r.text
    assert _tag_names_for_post(db, pid) == {"plain"}
    db.expire_all()
    assert db.get(Tag, miku.id).post_count == 0
    assert db.get(Tag, voc.id).post_count == 0


# --- regression: delete decrements post_count --------------------------------

def test_delete_post_decrements_post_count(client: TestClient, media_dir: Path, db) -> None:
    # audit #4: deleting a post decrements each of its tags' post_count
    # (clamped at 0) even though the post_tags rows go via FK CASCADE.
    _setup(client)
    p1 = _ingest(db, media_dir, (21, 22, 23))
    p2 = _ingest(db, media_dir, (24, 25, 26))
    tags.tag_post(db, p1, ["shared", "only_p1"])
    tags.tag_post(db, p2, ["shared"])

    # Force a drifted counter to prove the clamp: only_p1 has one post_tags
    # row but its counter already says 0.
    only = db.execute(select(Tag).where(Tag.name == "only_p1")).scalar_one()
    only.post_count = 0
    db.commit()

    r = client.delete(f"/api/posts/{p1}")
    assert r.status_code == 204

    db.expire_all()
    shared = db.execute(select(Tag).where(Tag.name == "shared")).scalar_one()
    assert shared.post_count == 1, "2 → 1 after deleting one of the two tagged posts"
    only = db.execute(select(Tag).where(Tag.name == "only_p1")).scalar_one()
    assert only.post_count == 0, "clamped at 0, not driven negative"


# --- regression: update_post is a single transaction -------------------------

def test_update_post_atomic_on_midway_failure(
    client: TestClient, media_dir: Path, db, monkeypatch
) -> None:
    # audit #9: a failure after the add phase must leave neither the rating
    # change nor the added tags behind — no committed union middle state.
    _setup(client)
    pid = _ingest(db, media_dir, (31, 32, 33))
    tags.tag_post(db, pid, ["orig"])

    real_tag_post = tags.tag_post

    def tag_post_then_boom(*args, **kwargs):
        real_tag_post(*args, **kwargs)
        raise RuntimeError("boom after add phase")

    monkeypatch.setattr(post_edit.tags, "tag_post", tag_post_then_boom)
    with pytest.raises(RuntimeError):
        post_edit.update_post(db, pid, tag_names=["orig", "added"], rating="explicit")

    db.expire_all()
    assert db.get(Post, pid).rating == "safe", "rating change must roll back"
    assert _tag_names_for_post(db, pid) == {"orig"}, "no old∪new union state"
    assert db.execute(
        select(Tag).where(Tag.name == "added")
    ).scalar_one_or_none() is None, "the new tag's get-or-create rolled back too"


# --- regression: tag get-or-create race --------------------------------------

def test_update_post_survives_tag_create_race(
    client: TestClient, media_dir: Path, db, monkeypatch
) -> None:
    # audit #32: a concurrent session committing the same new tag name between
    # our SELECT and flush must not fail the update — the pass is rerun and
    # adopts the winner's row.
    _setup(client)
    pid = _ingest(db, media_dir, (41, 42, 43))
    tags.tag_post(db, pid, ["orig"])

    other = db_module.SessionLocal()
    real_flush = db.flush
    fired: list[bool] = []

    def racing_flush(*args, **kwargs):
        pending_raced = any(isinstance(o, Tag) and o.name == "raced" for o in db.new)
        if pending_raced and not fired:
            fired.append(True)
            other.add(Tag(name="raced", category="general", post_count=0))
            other.commit()
        return real_flush(*args, **kwargs)

    monkeypatch.setattr(db, "flush", racing_flush)
    try:
        post_edit.update_post(db, pid, tag_names=["raced"])
    finally:
        other.close()

    assert fired, "the race must actually have been injected"
    assert _tag_names_for_post(db, pid) == {"raced"}
    rows = db.execute(select(Tag).where(Tag.name == "raced")).scalars().all()
    assert len(rows) == 1, "the winner's row is adopted — no duplicate tag"
    db.expire_all()
    assert db.get(Tag, rows[0].id).post_count == 1
    orig = db.execute(select(Tag).where(Tag.name == "orig")).scalar_one()
    assert orig.post_count == 0, "the replaced-away tag was still decremented"
