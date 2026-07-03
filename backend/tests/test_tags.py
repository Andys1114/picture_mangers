"""Tag write-side: implication materialization, cycle prevention, backfill,
post_count, and tag-resource CRUD endpoints (slice 2 remainder).

Covers AC1-AC7. Uses ``media.ingest`` (slice 3) to create real posts, then
exercises the write-side services + the /api/tags endpoints end to end.
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
from app.models.tag import PostTag, Tag, TagImplication
from app.services import media, tags
from app.services.errors import ConflictError


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
    """Create the single user and carry the session cookie on `client`."""
    client.post("/api/auth/setup", json={"username": "admin", "password": "pw12345678"})


def _png_bytes(w: int, h: int, rgb: tuple[int, int, int]) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (w, h), rgb).save(buf, format="PNG")
    return buf.getvalue()


def _ingest_post(db, media_dir: Path, rgb: tuple[int, int, int] = (10, 20, 30)) -> int:
    """Ingest a real post and return its id."""
    post = media.ingest(
        db, _png_bytes(200, 200, rgb),
        source_site="local", source_id=None, source_url=None,
        file_ext="png", is_animated=False,
    )
    return post.id


def _create_tag_ids(db, names: list[str]) -> dict[str, int]:
    """Create tags directly and return a name→id map (bypasses endpoints)."""
    out: dict[str, int] = {}
    for n in names:
        t = tags.create_tag(db, n, "general")
        out[n] = t.id
    return out


# --- AC1: tag_post materializes the closure --------------------------------

def test_tag_post_materializes_closure(client: TestClient, media_dir: Path, db) -> None:
    """AC1: build A→B, B→C implications; tagging a post with A writes the full
    closure {A,B,C} into post_tags and bumps each tag's post_count by 1."""
    ids = _create_tag_ids(db, ["a", "b", "c"])
    tags.create_implication(db, ids["a"], ids["b"])
    tags.create_implication(db, ids["b"], ids["c"])

    post_id = _ingest_post(db, media_dir)
    tags.tag_post(db, post_id, ["a"])

    tagged = {
        tid for (tid,) in db.execute(
            select(PostTag.tag_id).where(PostTag.post_id == post_id)
        ).all()
    }
    assert tagged == {ids["a"], ids["b"], ids["c"]}, f"expected full closure, got {tagged}"

    for name in ("a", "b", "c"):
        t = db.get(Tag, ids[name])
        assert t.post_count == 1, f"{name}.post_count should be 1, got {t.post_count}"


# --- AC2 + self-loop: cycle prevention -------------------------------------

def test_create_implication_cycle_rejected(client: TestClient, media_dir: Path, db) -> None:
    """AC2: after A→B, creating B→A raises ConflictError (409) and writes no
    new implication row."""
    ids = _create_tag_ids(db, ["a", "b"])
    tags.create_implication(db, ids["a"], ids["b"])

    before = db.execute(select(TagImplication)).scalars().all()
    with pytest.raises(ConflictError) as exc:
        tags.create_implication(db, ids["b"], ids["a"])
    assert exc.value.code == "conflict"
    assert exc.value.status_code == 409

    after = db.execute(select(TagImplication)).scalars().all()
    assert len(after) == len(before), "no new implication row should be written"


def test_self_loop_rejected(client: TestClient, media_dir: Path, db) -> None:
    """A→A is rejected as a self-loop (ConflictError 409)."""
    ids = _create_tag_ids(db, ["a"])
    with pytest.raises(ConflictError) as exc:
        tags.create_implication(db, ids["a"], ids["a"])
    assert exc.value.status_code == 409


# --- AC3: implication backfill ---------------------------------------------

def test_implication_backfill(client: TestClient, media_dir: Path, db) -> None:
    """AC3: tag a post with A (no implications yet), then create A→B; the post
    gains B in post_tags and B's post_count goes up by 1."""
    ids = _create_tag_ids(db, ["a", "b"])
    post_id = _ingest_post(db, media_dir, rgb=(1, 2, 3))
    tags.tag_post(db, post_id, ["a"])

    # Sanity: only A before the implication.
    assert {tid for (tid,) in db.execute(
        select(PostTag.tag_id).where(PostTag.post_id == post_id)
    ).all()} == {ids["a"]}
    assert db.get(Tag, ids["b"]).post_count == 0

    tags.create_implication(db, ids["a"], ids["b"])

    tagged = {tid for (tid,) in db.execute(
        select(PostTag.tag_id).where(PostTag.post_id == post_id)
    ).all()}
    assert ids["b"] in tagged, "backfill must add the consequent to existing posts"
    assert db.get(Tag, ids["b"]).post_count == 1


# --- AC5: post_count accurate + idempotent ---------------------------------

def test_post_count_accurate_and_idempotent(client: TestClient, media_dir: Path, db) -> None:
    """AC5: re-tagging the same post with an already-present tag does not double
    post_count; post_count always equals the number of post_tags rows."""
    ids = _create_tag_ids(db, ["solo"])
    post_id = _ingest_post(db, media_dir, rgb=(4, 5, 6))
    tags.tag_post(db, post_id, ["solo"])
    tags.tag_post(db, post_id, ["solo"])  # idempotent re-tag

    rows = db.execute(select(PostTag).where(PostTag.post_id == post_id)).scalars().all()
    assert len(rows) == 1, "composite PK dedupes the (post_id, tag_id) pair"
    assert db.get(Tag, ids["solo"]).post_count == 1


# --- AC6: tags CRUD endpoints ----------------------------------------------

def test_tags_crud_endpoints(client: TestClient, media_dir: Path, db) -> None:
    """AC6: POST/PATCH/GET list/GET detail/GET tree, plus 401 on no auth."""
    # 401 without a cookie on every endpoint.
    for method, path, body in (
        ("get", "/api/tags", None),
        ("get", "/api/tags/tree", None),
        ("get", "/api/tags/1", None),
        ("post", "/api/tags", {"name": "x", "category": "general"}),
        ("patch", "/api/tags/1", {"category": "artist"}),
    ):
        r = getattr(client, method)(path, json=body) if body else getattr(client, method)(path)
        assert r.status_code == 401, f"{method.upper()} {path} should require auth, got {r.status_code}"

    _setup(client)

    # POST a tag.
    r = client.post("/api/tags", json={"name": "hatsune_miku", "category": "character"})
    assert r.status_code == 201, r.text
    tag_id = r.json()["id"]
    assert r.json()["post_count"] == 0

    # POST duplicate name → 409.
    r = client.post("/api/tags", json={"name": "hatsune_miku", "category": "character"})
    assert r.status_code == 409
    assert r.json()["error"]["code"] == "conflict"

    # PATCH rename (collision) + recategorize.
    client.post("/api/tags", json={"name": "other", "category": "general"})
    r = client.patch(f"/api/tags/{tag_id}", json={"name": "other"})
    assert r.status_code == 409, "rename to a taken name must 409"
    r = client.patch(f"/api/tags/{tag_id}", json={"category": "artist"})
    assert r.status_code == 200
    assert r.json()["category"] == "artist"

    # GET list with search + order.
    r = client.get("/api/tags", params={"search": "miku", "order": "name"})
    assert r.status_code == 200
    names = [t["name"] for t in r.json()["data"]]
    assert "hatsune_miku" in names

    # GET detail.
    r = client.get(f"/api/tags/{tag_id}")
    assert r.status_code == 200
    assert r.json()["id"] == tag_id

    # GET detail of a missing tag → 404.
    r = client.get("/api/tags/999999")
    assert r.status_code == 404

    # GET tree (empty so far — just must be 200 + envelope shape).
    r = client.get("/api/tags/tree")
    assert r.status_code == 200
    assert "data" in r.json()


def test_tags_tree_structure(client: TestClient, media_dir: Path, db) -> None:
    """The /tree endpoint returns antecedent→[consequents] for an implication."""
    _setup(client)
    ids = _create_tag_ids(db, ["parent", "child"])
    tags.create_implication(db, ids["parent"], ids["child"])

    r = client.get("/api/tags/tree")
    assert r.status_code == 200
    nodes = r.json()["data"]
    parent_node = next(n for n in nodes if n["tag"]["name"] == "parent")
    assert [c["name"] for c in parent_node["consequents"]] == ["child"]


# --- AC7: end-to-end with search -------------------------------------------

def test_tag_post_end_to_end_with_search(client: TestClient, media_dir: Path, db) -> None:
    """AC7: ingest a post, tag it, and confirm GET /api/posts?tags=... finds it
    — the write side and the read side close the loop."""
    _setup(client)
    # Make safe_mode off so a non-safe-rating post is still searchable if needed.
    client.patch("/api/auth/me/settings", json={"safe_mode": False})

    ids = _create_tag_ids(db, ["blue_themed"])
    post_id = _ingest_post(db, media_dir, rgb=(0, 0, 255))
    tags.tag_post(db, post_id, ["blue_themed"])

    r = client.get("/api/posts", params={"tags": "blue_themed"})
    assert r.status_code == 200
    ids_returned = [p["id"] for p in r.json()["data"]]
    assert post_id in ids_returned, "tagged post must be searchable by its tag"

    # A different tag that the post does NOT have returns no match.
    r = client.get("/api/posts", params={"tags": "red_themed"})
    assert post_id not in [p["id"] for p in r.json()["data"]]
