"""Authenticated /media serving — the route that replaced the StaticFiles mount.

Covers: session-cookie requirement, immutable cache header, path-traversal
rejection, and 404 for missing files. URL shape stays /media/<relative path>
(the Next.js rewrite depends on it).
"""
from __future__ import annotations

import io
from pathlib import Path

import pytest
from PIL import Image
from fastapi.testclient import TestClient

from app import db as db_module
from app.config import settings
from app.services import media


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


def _png_bytes() -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (64, 64), (10, 20, 30)).save(buf, format="PNG")
    return buf.getvalue()


def _ingest_preview_path(db, media_dir: Path) -> str:
    """Ingest one post and return its preview's media-relative path."""
    post = media.ingest(
        db, _png_bytes(),
        source_site="local", source_id=None, source_url=None,
        file_ext="png", is_animated=False,
    )
    return post.preview_path


def test_media_requires_auth(client: TestClient, media_dir: Path, db) -> None:
    # audit #5: files must not be readable without a session cookie.
    rel = _ingest_preview_path(db, media_dir)
    r = client.get(f"/media/{rel}")
    assert r.status_code == 401
    assert r.json()["error"]["code"] == "unauthorized"

    _setup(client)
    assert client.get(f"/media/{rel}").status_code == 200


def test_media_serves_file_with_immutable_cache(client: TestClient, media_dir: Path, db) -> None:
    # audit #5 + #17: authenticated fetch returns the bytes on disk plus a
    # long-lived Cache-Control (posts/{id}/ files are immutable).
    _setup(client)
    rel = _ingest_preview_path(db, media_dir)
    r = client.get(f"/media/{rel}")
    assert r.status_code == 200
    assert r.content == (media_dir / rel).read_bytes()
    assert r.headers["cache-control"] == "public, max-age=31536000, immutable"


def test_media_blocks_path_traversal(client: TestClient, media_dir: Path, db) -> None:
    # audit #5: a real file one level above the media root must not be
    # reachable through encoded dot-segments (%2e%2e decodes to "..").
    _setup(client)
    secret = media_dir.parent / "outside.txt"
    secret.write_bytes(b"top secret")

    for path in ("/media/%2e%2e/outside.txt", "/media/posts/%2e%2e/%2e%2e/outside.txt"):
        r = client.get(path)
        assert r.status_code == 404, f"{path} must not escape the media dir"
        assert b"top secret" not in r.content


def test_media_missing_file_is_404_envelope(client: TestClient, media_dir: Path, db) -> None:
    # audit #5: missing files use the unified envelope, not a stack trace.
    _setup(client)
    r = client.get("/media/posts/999999/preview.png")
    assert r.status_code == 404
    assert r.json()["error"]["code"] == "not_found"
