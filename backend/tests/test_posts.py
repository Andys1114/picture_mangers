"""Posts list/detail + safe_mode injection + duplicate hiding + AND search.

Covers the browse-page backend contract. Implication materialization is
simulated by inserting both antecedent+consequent post_tags rows directly
(the write-time closure logic lands in a later subtask; search itself is a
plain AND over post_tags per ADR-0001).
"""
from __future__ import annotations

import logging

from fastapi.testclient import TestClient

from app import db as db_module
from app.models.post import Post
from app.models.tag import PostTag, Tag
from app.models.user import Session as SessionRow
from app.services import search


def _setup(client: TestClient) -> None:
    """Create the single user and carry the session cookie on `client`."""
    client.post("/api/auth/setup", json={"username": "admin", "password": "pw12345678"})


def _add_post(db, *, rating: str = "safe", md5: str, duplicate_of_id: int | None = None) -> int:  # type: ignore[no-untyped-def]
    """Insert a post and return its id (int) so callers don't hold a detached
    ORM instance across the session boundary (expire_on_commit is on)."""
    post = Post(
        source_site=None,
        source_id=None,
        source_url=None,
        file_path=f"posts/{md5}/original.png",
        thumb_path=f"posts/{md5}/thumb.png",
        preview_path=f"posts/{md5}/preview.png",
        file_ext="png",
        is_animated=False,
        width=600,
        height=800,
        file_size=1024,
        md5=md5,
        phash=None,
        is_duplicate=duplicate_of_id is not None,
        duplicate_of_id=duplicate_of_id,
        rating=rating,
    )
    db.add(post)
    db.commit()
    db.refresh(post)
    return post.id


def _tag_post(db, post_id: int, names: list[tuple[str, str]]) -> None:  # type: ignore[no-untyped-def]
    """Attach tags [(name, category)] to a post via post_tags (materialized set)."""
    from sqlalchemy import select

    for name, category in names:
        tag = db.execute(select(Tag).where(Tag.name == name)).scalar_one_or_none()
        if tag is None:
            tag = Tag(name=name, category=category, post_count=0)
            db.add(tag)
            db.commit()
            db.refresh(tag)
        db.add(PostTag(post_id=post_id, tag_id=tag.id))
    db.commit()


def test_list_requires_auth(client: TestClient) -> None:
    """AC: GET /api/posts without a session cookie is 401."""
    r = client.get("/api/posts")
    assert r.status_code == 401
    assert r.json()["error"]["code"] == "unauthorized"


def test_list_empty(client: TestClient) -> None:
    """AC: authenticated list on an empty gallery returns empty data + meta."""
    _setup(client)
    r = client.get("/api/posts")
    assert r.status_code == 200
    body = r.json()
    assert body == {"data": [], "meta": {"page": 1, "total": 0}}


def test_safe_mode_injects_safe_filter(client: TestClient) -> None:
    """AC: safe_mode=True (default) hides questionable/explicit from the list."""
    _setup(client)
    with db_module.SessionLocal() as db:
        _add_post(db, rating="safe", md5="a" * 32)
        _add_post(db, rating="questionable", md5="b" * 32)
        _add_post(db, rating="explicit", md5="c" * 32)
    r = client.get("/api/posts")
    assert r.status_code == 200
    ratings = {p["rating"] for p in r.json()["data"]}
    assert ratings == {"safe"}
    assert r.json()["meta"]["total"] == 1


def test_safe_mode_off_shows_all(client: TestClient) -> None:
    """AC: PATCH /me/settings {safe_mode:false} lets all ratings through."""
    _setup(client)
    with db_module.SessionLocal() as db:
        _add_post(db, rating="safe", md5="a" * 32)
        _add_post(db, rating="explicit", md5="b" * 32)
    assert client.patch("/api/auth/me/settings", json={"safe_mode": False}).status_code == 200
    r = client.get("/api/posts")
    ratings = {p["rating"] for p in r.json()["data"]}
    assert ratings == {"safe", "explicit"}
    assert r.json()["meta"]["total"] == 2


def test_duplicates_hidden_by_default(client: TestClient) -> None:
    """AC: posts with duplicate_of_id set are excluded from the main view."""
    _setup(client)
    with db_module.SessionLocal() as db:
        original_id = _add_post(db, rating="safe", md5="a" * 32)
        _add_post(db, rating="safe", md5="b" * 32, duplicate_of_id=original_id)
    r = client.get("/api/posts")
    assert r.json()["meta"]["total"] == 1
    assert r.json()["data"][0]["id"] == original_id


def test_and_search_over_post_tags(client: TestClient) -> None:
    """AC: ?tags=a b returns only posts with BOTH tags (materialized post_tags)."""
    _setup(client)
    with db_module.SessionLocal() as db:
        p1 = _add_post(db, rating="safe", md5="a" * 32)
        p2 = _add_post(db, rating="safe", md5="b" * 32)
        p3 = _add_post(db, rating="safe", md5="c" * 32)
        _tag_post(db, p1, [("miku", "character"), ("vocaloid", "copyright")])
        _tag_post(db, p2, [("miku", "character")])
        _tag_post(db, p3, [("vocaloid", "copyright")])
    # miku AND vocaloid -> only p1
    r = client.get("/api/posts", params={"tags": "miku vocaloid"})
    assert r.json()["meta"]["total"] == 1
    assert r.json()["data"][0]["id"] == p1
    # miku alone -> p1 and p2
    r = client.get("/api/posts", params={"tags": "miku"})
    assert r.json()["meta"]["total"] == 2


def test_implication_materialized_set_is_searched_directly(client: TestClient) -> None:
    """AC (ADR-0001): searching the consequent (vocaloid) hits a post whose
    logical tag was the antecedent (miku), because post_tags already holds the
    expanded set. No read-time recursion. Here we simulate the write-time
    materialization by inserting both rows."""
    _setup(client)
    with db_module.SessionLocal() as db:
        post_id = _add_post(db, rating="safe", md5="a" * 32)
        # User "tagged" miku; write-time closure would also insert vocaloid.
        _tag_post(db, post_id, [("miku", "character"), ("vocaloid", "copyright")])
    r = client.get("/api/posts", params={"tags": "vocaloid"})
    assert r.json()["meta"]["total"] == 1
    assert r.json()["data"][0]["id"] == post_id


def test_pagination(client: TestClient) -> None:
    """AC: page+limit slicing + total reflect the full matching set."""
    _setup(client)
    with db_module.SessionLocal() as db:
        for i in range(5):
            _add_post(db, rating="safe", md5=hex(i)[2:].rjust(32, "0"))
    r = client.get("/api/posts", params={"page": 1, "limit": 2})
    body = r.json()
    assert body["meta"] == {"page": 1, "total": 5}
    assert len(body["data"]) == 2
    # newest first (id desc)
    assert body["data"][0]["id"] > body["data"][1]["id"]


def test_detail_returns_tags_and_404(client: TestClient) -> None:
    """AC: /api/posts/{id} returns the post with its expanded tag set; missing -> 404."""
    _setup(client)
    with db_module.SessionLocal() as db:
        post_id = _add_post(db, rating="safe", md5="a" * 32)
        _tag_post(db, post_id, [("miku", "character")])
    r = client.get(f"/api/posts/{post_id}")
    assert r.status_code == 200
    body = r.json()
    assert body["id"] == post_id
    assert body["md5"] == "a" * 32
    assert [t["name"] for t in body["tags"]] == ["miku"]

    missing = client.get("/api/posts/999999")
    assert missing.status_code == 404
    assert missing.json()["error"]["code"] == "not_found"


def test_me_returns_safe_mode(client: TestClient) -> None:
    """AC: /me includes safe_mode; new session defaults to True."""
    _setup(client)
    r = client.get("/api/auth/me")
    assert r.status_code == 200
    body = r.json()
    assert body["username"] == "admin"
    assert body["safe_mode"] is True


def test_settings_requires_auth(client: TestClient) -> None:
    """AC: PATCH /me/settings without a cookie is 401."""
    r = client.patch("/api/auth/me/settings", json={"safe_mode": False})
    assert r.status_code == 401


def test_token_row_survives_safe_mode_off(client: TestClient) -> None:
    """Regression: turning safe_mode off must not invalidate the session."""
    _setup(client)
    token = client.cookies["gallery_session"]
    assert client.patch("/api/auth/me/settings", json={"safe_mode": False}).status_code == 200
    # same cookie still authenticates
    assert client.get("/api/auth/me").status_code == 200
    # and the row reflects the new value
    with db_module.SessionLocal() as db:
        row = db.get(SessionRow, token)
        assert row is not None
        assert row.safe_mode is False


def test_favorite_field_derived_from_membership(client: TestClient) -> None:
    # audit #10 + #31: list/detail/patch derive `favorite` from the default
    # collection's favorite_items membership (no more hardcoded False).
    _setup(client)
    with db_module.SessionLocal() as db:
        starred_id = _add_post(db, rating="safe", md5="a" * 32)
        plain_id = _add_post(db, rating="safe", md5="b" * 32)

    # Nothing starred yet — everything reads False.
    by_id = {p["id"]: p["favorite"] for p in client.get("/api/posts").json()["data"]}
    assert by_id == {starred_id: False, plain_id: False}

    assert client.post(f"/api/posts/{starred_id}/favorite").json()["favorited"] is True

    # List reflects membership per post.
    by_id = {p["id"]: p["favorite"] for p in client.get("/api/posts").json()["data"]}
    assert by_id == {starred_id: True, plain_id: False}
    # Detail too.
    assert client.get(f"/api/posts/{starred_id}").json()["favorite"] is True
    assert client.get(f"/api/posts/{plain_id}").json()["favorite"] is False
    # PATCH response too.
    r = client.patch(f"/api/posts/{starred_id}", json={"rating": "safe"})
    assert r.status_code == 200
    assert r.json()["favorite"] is True

    # Unstar — reads flip back to False.
    assert client.post(f"/api/posts/{starred_id}/favorite").json()["favorited"] is False
    assert client.get(f"/api/posts/{starred_id}").json()["favorite"] is False


def test_safe_mode_covers_detail_and_next(client: TestClient) -> None:
    # audit #30: safe_mode also applies to GET /posts/{id} and /posts/{id}/next,
    # not just the list view.
    _setup(client)  # fresh session defaults to safe_mode=True
    with db_module.SessionLocal() as db:
        safe_old = _add_post(db, rating="safe", md5="a" * 32)
        explicit = _add_post(db, rating="explicit", md5="b" * 32)
        safe_new = _add_post(db, rating="safe", md5="c" * 32)

    # Detail of a non-safe post 404s while safe_mode is on.
    r = client.get(f"/api/posts/{explicit}")
    assert r.status_code == 404
    assert r.json()["error"]["code"] == "not_found"
    # ...and so does its /next (the current post itself is hidden).
    assert client.get(f"/api/posts/{explicit}/next").status_code == 404

    # Navigation skips the explicit post in both directions.
    assert client.get(f"/api/posts/{safe_new}/next").json() == {
        "prev_id": None,
        "next_id": safe_old,
    }
    assert client.get(f"/api/posts/{safe_old}/next").json() == {
        "prev_id": safe_new,
        "next_id": None,
    }

    # safe_mode off — detail and adjacency see the explicit post again.
    assert client.patch("/api/auth/me/settings", json={"safe_mode": False}).status_code == 200
    assert client.get(f"/api/posts/{explicit}").status_code == 200
    assert client.get(f"/api/posts/{safe_new}/next").json()["next_id"] == explicit


def _seed_one_per_rating(client: TestClient) -> None:
    """Setup + one post of each rating (safe/questionable/explicit)."""
    _setup(client)
    with db_module.SessionLocal() as db:
        _add_post(db, rating="safe", md5="a" * 32)
        _add_post(db, rating="questionable", md5="b" * 32)
        _add_post(db, rating="explicit", md5="c" * 32)


def test_ratings_param_ignored_while_safe_mode_on(client: TestClient) -> None:
    """AC: safe mode on -> ?ratings=explicit is ignored, only safe returned
    (server-authoritative injection unchanged)."""
    _seed_one_per_rating(client)  # fresh session defaults to safe_mode=True
    r = client.get("/api/posts", params={"ratings": "explicit"})
    assert r.status_code == 200
    assert {p["rating"] for p in r.json()["data"]} == {"safe"}
    assert r.json()["meta"]["total"] == 1


def test_ratings_param_filters_when_safe_mode_off(client: TestClient) -> None:
    """AC: safe mode off -> ?ratings=safe,questionable excludes explicit."""
    _seed_one_per_rating(client)
    assert client.patch("/api/auth/me/settings", json={"safe_mode": False}).status_code == 200
    r = client.get("/api/posts", params={"ratings": "safe,questionable"})
    assert r.status_code == 200
    assert {p["rating"] for p in r.json()["data"]} == {"safe", "questionable"}
    assert r.json()["meta"]["total"] == 2


def test_ratings_param_default_returns_all(client: TestClient) -> None:
    """AC: safe mode off + no ratings param -> all ratings come back."""
    _seed_one_per_rating(client)
    assert client.patch("/api/auth/me/settings", json={"safe_mode": False}).status_code == 200
    r = client.get("/api/posts")
    assert r.status_code == 200
    assert {p["rating"] for p in r.json()["data"]} == {"safe", "questionable", "explicit"}
    assert r.json()["meta"]["total"] == 3


def test_ratings_param_invalid_value_422(client: TestClient) -> None:
    """AC: ?ratings=foo fails validation with the unified 422 envelope."""
    _setup(client)
    r = client.get("/api/posts", params={"ratings": "foo"})
    assert r.status_code == 422
    body = r.json()
    assert body["error"]["code"] == "validation_error"
    assert "ratings" in body["error"]["message"]


def test_validation_error_uses_envelope(client: TestClient) -> None:
    # audit #16: FastAPI request-validation failures (422) must use the
    # unified error envelope instead of the default {"detail": [...]}.
    _setup(client)
    r = client.get("/api/posts", params={"page": 0})
    assert r.status_code == 422
    body = r.json()
    assert "detail" not in body
    assert body["error"]["code"] == "validation_error"
    assert "page" in body["error"]["message"]


def test_unhandled_exception_is_logged_and_enveloped(
    client: TestClient, monkeypatch, caplog
) -> None:
    # audit #39: the catch-all handler records the traceback server-side while
    # the client still gets the generic 500 envelope.
    _setup(client)
    token = client.cookies["gallery_session"]

    def boom(*args, **kwargs):  # type: ignore[no-untyped-def]
        raise RuntimeError("boom")

    monkeypatch.setattr(search, "list_posts", boom)
    from app.main import app

    with TestClient(app, raise_server_exceptions=False) as c:
        c.cookies.set("gallery_session", token)
        with caplog.at_level(logging.ERROR, logger="app.services.errors"):
            r = c.get("/api/posts")

    assert r.status_code == 500
    assert r.json() == {"error": {"code": "internal_error", "message": "服务器内部错误"}}
    records = [rec for rec in caplog.records if rec.name == "app.services.errors"]
    assert records, "unhandled exception must be logged"
    assert records[0].levelname == "ERROR"
    assert "unhandled exception" in records[0].getMessage()
    assert records[0].exc_info is not None, "traceback must be attached"
