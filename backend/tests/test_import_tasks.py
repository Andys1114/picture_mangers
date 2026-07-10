"""Import/task scheduling tests (slice 8 backend).

Patches the scheduler to run jobs synchronously (add_job → immediate call) so
tests are deterministic without real threads. Covers scan end-to-end,
incremental skip, scrape with a fake scraper, cancel, concurrency, and auth.
"""
from __future__ import annotations

import io
import logging
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


# --- audit regression tests --------------------------------------------------

class _DeferredScheduler:
    """Fake scheduler that queues jobs until run_all() — lets tests observe
    pending tasks (cancel, dedup, shutdown broadcast) deterministically."""

    def __init__(self) -> None:
        self._jobs: list[tuple] = []

    def add_job(self, func, args=None, **_) -> None:
        self._jobs.append((func, args or []))

    def run_all(self) -> None:
        for func, args in self._jobs:
            func(*args)
        self._jobs.clear()

    def shutdown(self, wait: bool = False) -> None:
        pass


def test_scan_ingest_failure_rolls_back_dirty_session(
    client: TestClient, media_dir: Path, db, sync_scheduler, monkeypatch, caplog
) -> None:
    # audit #1 #2 #7: a mid-ingest failure (Post flushed, file write fails) must
    # be rolled back — the orphan row must not ride along with the next file's
    # commit. audit #28: the failure is logged with the file path.
    _setup(client)
    scan_root = media_dir.parent / "rollback_src"
    scan_root.mkdir()
    _write_png(scan_root / "a.png", (10, 20, 30))
    _write_png(scan_root / "b.png", (40, 50, 60))

    real_write = Path.write_bytes
    fail_once = {"armed": True}

    def flaky_write(self: Path, data: bytes):
        # Fail the first original-image write (after db.flush in media.ingest).
        if fail_once["armed"] and self.name.startswith("original"):
            fail_once["armed"] = False
            raise OSError("disk full")
        return real_write(self, data)

    monkeypatch.setattr(Path, "write_bytes", flaky_write)

    with caplog.at_level(logging.WARNING, logger="app.services.import_service"):
        r = client.post("/api/import/scan", json={"path": str(scan_root)})
    tid = r.json()["task_id"]
    s = client.get(f"/api/tasks/{tid}").json()
    assert s["status"] == "completed"
    assert s["failed"] == 1 and s["total"] == 2 and s["processed"] == 2

    rows = db.execute(select(Post)).scalars().all()
    assert len(rows) == 1, "half-ingested Post must not be committed by the next file"
    assert rows[0].file_path != ""

    assert any(
        "ingest failed" in rec.getMessage() and str(scan_root / "a.png") in rec.getMessage()
        for rec in caplog.records
    ), "per-file failure must be logged with the path"  # audit #28


def test_scan_duplicate_recorded_in_scan_history(
    client: TestClient, media_dir: Path, db, sync_scheduler
) -> None:
    # audit #8: md5-duplicate files also get a scan_history row, so a re-scan
    # mtime-skips them instead of re-reading + re-hashing every time.
    _setup(client)
    scan_root = media_dir.parent / "dup_src"
    scan_root.mkdir()
    _write_png(scan_root / "a.png", (7, 7, 7))
    (scan_root / "b.png").write_bytes((scan_root / "a.png").read_bytes())  # same md5

    r = client.post("/api/import/scan", json={"path": str(scan_root)})
    s = client.get(f"/api/tasks/{r.json()['task_id']}").json()
    assert s["status"] == "completed"
    assert s["duplicates"] == 1

    hist_paths = {h.path for h in db.execute(select(ScanHistory)).scalars().all()}
    assert hist_paths == {str(scan_root / "a.png"), str(scan_root / "b.png")}

    # Re-scan: the duplicate is now mtime-skipped — not re-counted as duplicate.
    r2 = client.post("/api/import/scan", json={"path": str(scan_root)})
    s2 = client.get(f"/api/tasks/{r2.json()['task_id']}").json()
    assert s2["status"] == "completed"
    assert s2["processed"] == 2 and s2["duplicates"] == 0


def test_scan_survives_stat_failure_on_listing(
    client: TestClient, media_dir: Path, db, sync_scheduler, monkeypatch
) -> None:
    # audit #26 #27: a file vanishing between the walk and the stat is skipped;
    # the whole task must not fail.
    _setup(client)
    scan_root = media_dir.parent / "stat_src"
    scan_root.mkdir()
    _write_png(scan_root / "good.png", (1, 2, 3))
    _write_png(scan_root / "ghost.png", (4, 5, 6))

    real_stat = Path.stat

    def flaky_stat(self: Path, **kwargs):
        if self.name == "ghost.png":
            raise FileNotFoundError(str(self))
        return real_stat(self, **kwargs)

    monkeypatch.setattr(Path, "stat", flaky_stat)

    r = client.post("/api/import/scan", json={"path": str(scan_root)})
    s = client.get(f"/api/tasks/{r.json()['task_id']}").json()
    assert s["status"] == "completed", "a vanished file must not fail the whole task"
    assert s["total"] == 1 and s["processed"] == 1
    assert len(db.execute(select(Post)).scalars().all()) == 1


def test_request_length_bounds(client: TestClient, media_dir: Path, db, sync_scheduler) -> None:
    # audit #29: ScanRequest.path ≤ 1024, ScrapeRequest.query ≤ 512.
    _setup(client)
    r = client.post("/api/import/scan", json={"path": "x" * 1025})
    assert r.status_code == 422
    r = client.post("/api/import/scrape", json={"query": "y" * 513, "source": "danbooru", "limit": 1})
    assert r.status_code == 422
    # Boundary values are still accepted.
    r = client.post("/api/import/scan", json={"path": "x" * 1024})
    assert r.status_code == 201


def test_duplicate_submission_returns_existing_task(
    client: TestClient, media_dir: Path, db, sync_scheduler, monkeypatch
) -> None:
    # audit #34: resubmitting the same kind+params while pending/running returns
    # the existing task id and queues no second worker.
    _setup(client)
    sched = _DeferredScheduler()
    monkeypatch.setattr(task_svc, "_scheduler", sched)

    scan_root = media_dir.parent / "dedup_src"; scan_root.mkdir()
    other_root = media_dir.parent / "dedup_other"; other_root.mkdir()

    id1 = client.post("/api/import/scan", json={"path": str(scan_root)}).json()["task_id"]
    id2 = client.post("/api/import/scan", json={"path": str(scan_root)}).json()["task_id"]
    assert id1 == id2, "same pending scan path → same task id"
    id3 = client.post("/api/import/scan", json={"path": str(other_root)}).json()["task_id"]
    assert id3 != id1
    assert len(sched._jobs) == 2, "the duplicate submission must not queue a job"

    sched.run_all()
    assert client.get(f"/api/tasks/{id1}").json()["status"] == "completed"
    id4 = client.post("/api/import/scan", json={"path": str(scan_root)}).json()["task_id"]
    assert id4 != id1, "a finished task no longer dedups"

    # Scrape dedup keys on (query, limit). Jobs stay queued — never run, no network.
    s1 = client.post("/api/import/scrape", json={"query": "q", "source": "danbooru", "limit": 5}).json()["task_id"]
    s2 = client.post("/api/import/scrape", json={"query": "q", "source": "danbooru", "limit": 5}).json()["task_id"]
    s3 = client.post("/api/import/scrape", json={"query": "q", "source": "danbooru", "limit": 6}).json()["task_id"]
    assert s1 == s2
    assert s3 != s1


def test_shutdown_broadcasts_cancel_to_inflight_tasks(sync_scheduler, monkeypatch) -> None:
    # audit #35: shutdown_scheduler flags every task cancel_requested before
    # stopping the pool, so workers exit at their next poll.
    sched = _DeferredScheduler()
    monkeypatch.setattr(task_svc, "_scheduler", sched)

    tid = task_svc.submit_scan("C:/nonexistent-dir-for-shutdown-test")
    state = task_svc.get_task(tid)
    assert state is not None and state.cancel_requested is False

    task_svc.shutdown_scheduler()
    assert state.cancel_requested is True


def test_failed_scan_error_is_generic_and_logged(
    client: TestClient, media_dir: Path, db, sync_scheduler, monkeypatch, caplog
) -> None:
    # audit #36: str(exc) must not reach the API response; the original
    # exception goes to the server log instead. audit #39: failure logged at ERROR.
    _setup(client)
    import app.services.import_service as import_service_mod

    def boom(*args, **kwargs):
        raise RuntimeError("OperationalError: sqlite at D:\\private\\pictures.db")

    monkeypatch.setattr(import_service_mod, "scan_directory", boom)

    with caplog.at_level(logging.ERROR, logger="app.services.tasks"):
        r = client.post("/api/import/scan", json={"path": str(media_dir)})
    s = client.get(f"/api/tasks/{r.json()['task_id']}").json()
    assert s["status"] == "failed"
    assert s["error"] == "导入失败，请查看服务器日志"
    assert "private" not in s["error"] and "OperationalError" not in s["error"]

    failure_logs = [rec for rec in caplog.records if "scan task failed" in rec.getMessage()]
    assert failure_logs, "failure must be logged server-side"
    assert any(rec.exc_info for rec in failure_logs), "original exception recorded with traceback"


def test_failed_scrape_error_is_generic(
    client: TestClient, media_dir: Path, db, sync_scheduler, monkeypatch
) -> None:
    # audit #36: scrape worker failures also return a generic message.
    _setup(client)
    import app.scrapers.danbooru as danbooru_mod

    class _BoomScraper:
        def __init__(self) -> None:
            raise RuntimeError("connection refused to 10.0.0.1")

    monkeypatch.setattr(danbooru_mod, "DanbooruScraper", _BoomScraper)

    r = client.post("/api/import/scrape", json={"query": "x", "source": "danbooru", "limit": 1})
    s = client.get(f"/api/tasks/{r.json()['task_id']}").json()
    assert s["status"] == "failed"
    assert s["error"] == "抓取失败，请查看服务器日志"
    assert "10.0.0.1" not in s["error"]


def test_task_lifecycle_logged(client: TestClient, media_dir: Path, db, sync_scheduler, caplog) -> None:
    # audit #39 (W1 portion): task started/finished are logged at INFO.
    _setup(client)
    scan_root = media_dir.parent / "log_src"
    scan_root.mkdir()
    _write_png(scan_root / "a.png", (3, 3, 3))

    with caplog.at_level(logging.INFO, logger="app.services.tasks"):
        r = client.post("/api/import/scan", json={"path": str(scan_root)})
    tid = r.json()["task_id"]
    msgs = [rec.getMessage() for rec in caplog.records]
    assert any(f"scan task started task_id={tid}" in m for m in msgs)
    assert any(f"scan task finished task_id={tid}" in m and "status=completed" in m for m in msgs)
