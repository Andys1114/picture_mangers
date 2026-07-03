"""Import/task scheduling tests (slice 8 backend).

Patches the scheduler to run jobs synchronously (add_job → immediate call) so
tests are deterministic without real threads. Covers scan end-to-end,
incremental skip, scrape with a fake scraper, cancel, concurrency, and auth.
"""
from __future__ import annotations

import io
import os
import time
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from PIL import Image
from sqlalchemy import select
from fastapi.testclient import TestClient

from app import db as db_module
from app.config import settings
from app.models.post import Post
from app.models.scan_history import ScanHistory
from app.services import tasks as task_svc
from app.services.errors import ScraperError


# --- fixtures --------------------------------------------------------------

@pytest.fixture()
def media_dir(tmp_path, monkeypatch) -> Path:
    d = tmp_path / "media"
    d.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(settings, "media_dir", str(d))
    return settings.media_path


@pytest.fixture()
def sync_scheduler(monkeypatch):
    """Replace the APScheduler with a synchronous executor: add_job calls the
    target immediately. Keeps tests deterministic (no threads, no polling)."""
    class _SyncScheduler:
        def add_job(self, func, args=None, kwargs=None, **_):
            func(*(args or []), **(kwargs or {}))
        def shutdown(self, wait=False):
            pass

    monkeypatch.setattr(task_svc, "_scheduler", _SyncScheduler())
    # Reset the task registry between tests.
    monkeypatch.setattr(task_svc, "_tasks", {})
    return _SyncScheduler()


@pytest.fixture()
def db():
    s = db_module.SessionLocal()
    try:
        yield s
    finally:
        s.close()


def _setup(client: TestClient) -> None:
    client.post("/api/auth/setup", json={"username": "admin", "password": "pw12345678"})


def _write_png(path: Path, rgb: tuple[int, int, int]) -> None:
    buf = io.BytesIO()
    Image.new("RGB", (50, 50), rgb).save(buf, format="PNG")
    path.write_bytes(buf.getvalue())


# --- AC2 + AC3: scan end-to-end + progress ---------------------------------

def test_scan_end_to_end(client: TestClient, media_dir: Path, db, sync_scheduler) -> None:
    """AC2+AC3: scan a folder of 2 PNGs → both ingested, scan_history recorded,
    task completed with processed=total=2."""
    _setup(client)
    scan_root = media_dir.parent / "scan_src"
    scan_root.mkdir()
    _write_png(scan_root / "a.png", (1, 2, 3))
    _write_png(scan_root / "b.png", (4, 5, 6))

    r = client.post("/api/import/scan", json={"path": str(scan_root)})
    assert r.status_code == 201, r.text
    task_id = r.json()["task_id"]

    # Sync scheduler already ran the job — status should be completed.
    r = client.get(f"/api/tasks/{task_id}")
    assert r.status_code == 200
    s = r.json()
    assert s["status"] == "completed"
    assert s["total"] == 2 and s["processed"] == 2
    assert s["duplicates"] == 0 and s["failed"] == 0

    # Two posts ingested + two scan_history rows.
    assert db.execute(select(Post)).scalars().all().__len__() == 2
    assert db.execute(select(ScanHistory)).scalars().all().__len__() == 2


def test_scan_incremental_skip(client: TestClient, media_dir: Path, db, sync_scheduler) -> None:
    """AC2: a second scan of the same unchanged files skips ingest (no new
    posts), but processed still advances."""
    _setup(client)
    scan_root = media_dir.parent / "scan_src2"
    scan_root.mkdir()
    p = scan_root / "x.png"
    _write_png(p, (9, 8, 7))

    client.post("/api/import/scan", json={"path": str(scan_root)})
    posts_after_first = db.execute(select(Post)).scalars().all().__len__()
    assert posts_after_first == 1

    # Second scan — same file, unchanged mtime → skip.
    r = client.post("/api/import/scan", json={"path": str(scan_root)})
    tid = r.json()["task_id"]
    r = client.get(f"/api/tasks/{tid}")
    assert r.json()["status"] == "completed"
    assert r.json()["processed"] == 1 and r.json()["total"] == 1
    assert db.execute(select(Post)).scalars().all().__len__() == 1, "no new post on incremental scan"


# --- AC4: scrape with a fake scraper ---------------------------------------

def test_scrape_with_fake_scraper(client: TestClient, media_dir: Path, db, sync_scheduler, monkeypatch) -> None:
    """AC4: POST /import/scrape runs scrape_to_db with a fake scraper (no real
    network). The task completes and counts reflect the fake's posts."""
    from app.scrapers.base import ScrapedPost, ScrapedTag, Scraper
    from app.services import scrape as scrape_svc

    class _Fake(Scraper):
        source_site = "danbooru"
        def __init__(self):
            self._bytes = b""
            buf = io.BytesIO(); Image.new("RGB",(30,30),(10,20,30)).save(buf,"PNG")
            self._bytes = buf.getvalue()
        def search(self, query, *, page=1, limit=100):
            return [ScrapedPost(source_id="1", image_url="u", tags=[ScrapedTag("t","general")],
                                rating="safe", source_url="s", file_ext="png", is_animated=False)]
        def fetch(self, source_id): return self.search("")[0]
        def download(self, image_url): return self._bytes
        def fetch_implications(self): return []

    # Patch DanbooruScraper in the tasks worker to use the fake.
    import app.services.tasks as tasks_mod
    monkeypatch.setattr(tasks_mod, "DanbooruScraper", _Fake, raising=False)
    # The worker imports DanbooruScraper lazily inside _run_scrape; patch the name it looks up.
    import app.scrapers.danbooru as danbooru_mod
    monkeypatch.setattr(danbooru_mod, "DanbooruScraper", _Fake)

    _setup(client)
    r = client.post("/api/import/scrape", json={"query": "test", "source": "danbooru", "limit": 1})
    assert r.status_code == 201
    tid = r.json()["task_id"]
    r = client.get(f"/api/tasks/{tid}")
    assert r.json()["status"] == "completed"
    assert r.json()["processed"] == 1
    assert db.execute(select(Post).where(Post.source_site == "danbooru")).first() is not None


# --- AC5: cancel -----------------------------------------------------------

def test_task_cancel(client: TestClient, media_dir: Path, db, sync_scheduler) -> None:
    """AC5: POST /tasks/{id}/cancel on a pending/running task sets the flag.
    (With the sync scheduler the job already ran, so cancel returns False for a
    completed task; verify the flag path by cancelling before run via a
    custom scheduler that defers.)"""
    _setup(client)
    # Use a deferred scheduler so the task is still pending when we cancel.
    class _Deferred:
        def __init__(self): self._jobs = []
        def add_job(self, func, args=None, **_): self._jobs.append((func, args or []))
        def run_all(self):
            for func, args in self._jobs:
                func(*args)
            self._jobs.clear()
        def shutdown(self, wait=False): pass
    import app.services.tasks as tasks_mod
    sched = _Deferred()
    tasks_mod._scheduler = sched

    scan_root = media_dir.parent / "cancel_src"
    scan_root.mkdir()
    _write_png(scan_root / "c.png", (1, 1, 1))

    r = client.post("/api/import/scan", json={"path": str(scan_root)})
    tid = r.json()["task_id"]
    # Task is pending (deferred). Cancel it.
    r = client.post(f"/api/tasks/{tid}/cancel")
    assert r.json()["cancelled"] is True
    # Now run the deferred job — it should observe cancel_requested and exit.
    sched.run_all()
    r = client.get(f"/api/tasks/{tid}")
    assert r.json()["status"] == "cancelled"


# --- AC6: concurrent tasks -------------------------------------------------

def test_concurrent_tasks(client: TestClient, media_dir: Path, db, sync_scheduler) -> None:
    """AC6: two scan tasks submitted back-to-back both register (distinct ids,
    both complete). The sync scheduler runs them serially but both succeed."""
    _setup(client)
    root1 = media_dir.parent / "c1"; root1.mkdir(); _write_png(root1 / "a.png", (1,1,1))
    root2 = media_dir.parent / "c2"; root2.mkdir(); _write_png(root2 / "b.png", (2,2,2))

    r1 = client.post("/api/import/scan", json={"path": str(root1)})
    r2 = client.post("/api/import/scan", json={"path": str(root2)})
    id1, id2 = r1.json()["task_id"], r2.json()["task_id"]
    assert id1 != id2
    assert client.get(f"/api/tasks/{id1}").json()["status"] == "completed"
    assert client.get(f"/api/tasks/{id2}").json()["status"] == "completed"
    assert db.execute(select(Post)).scalars().all().__len__() == 2


# --- AC7: auth --------------------------------------------------------------

def test_import_requires_auth(client: TestClient, media_dir: Path, db, sync_scheduler) -> None:
    """AC7: all import/tasks endpoints 401 without a cookie."""
    for method, path, kwargs in (
        ("post", "/api/import/scan", {"json": {"path": "/tmp"}}),
        ("post", "/api/import/scrape", {"json": {"query": "x", "source": "danbooru", "limit": 1}}),
        ("get", "/api/tasks/abc", {}),
        ("post", "/api/tasks/abc/cancel", {}),
    ):
        r = getattr(client, method)(path, **kwargs)
        assert r.status_code == 401, f"{method.upper()} {path} needs auth, got {r.status_code}"
