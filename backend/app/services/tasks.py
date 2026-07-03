"""Task scheduling kernel: APScheduler BackgroundScheduler + in-memory task state.

Holds the single BackgroundScheduler (max_workers=3, supports concurrent tasks)
and a module-level dict of task states. Task state is in-memory only — process
restart drops running/pending tasks (acceptable per design.md §4: "单机够用").

Cancellation is cooperative: ``cancel_task`` sets a flag the worker loop polls.
The worker exits at the next file boundary, marking the task ``cancelled``.

The DB session inside a worker is independent of any request session (created
fresh via ``SessionLocal()``) — SQLAlchemy sessions are not thread-safe and
must not cross request/worker boundaries.
"""
from __future__ import annotations

import secrets
import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone

from apscheduler.executors.pool import ThreadPoolExecutor
from apscheduler.schedulers.background import BackgroundScheduler


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


@dataclass
class TaskState:
    """Mutable per-task progress + control flags. Updated by the worker thread;
    read by the API thread. The ``_tasks_lock`` guards dict mutation; field
    writes are individually atomic enough for progress polling (GIL)."""

    task_id: str
    kind: str  # "scan" | "scrape"
    status: str = "pending"  # pending|running|completed|failed|cancelled
    processed: int = 0
    total: int = 0
    duplicates: int = 0
    failed: int = 0
    error: str | None = None
    cancel_requested: bool = False
    started_at: datetime = field(default_factory=_now)
    finished_at: datetime | None = None


_tasks: dict[str, TaskState] = {}
_tasks_lock = threading.Lock()

_scheduler: BackgroundScheduler | None = None


def _get_scheduler() -> BackgroundScheduler:
    """Lazily build (and start) the singleton scheduler. Started on first use
    so tests that patch it never spin up a real thread pool."""
    global _scheduler
    if _scheduler is None:
        _scheduler = BackgroundScheduler(
            executors={"default": ThreadPoolExecutor(max_workers=3)},
            timezone="UTC",
        )
        _scheduler.start()
    return _scheduler


def shutdown_scheduler() -> None:
    """Stop the scheduler (call on app shutdown)."""
    global _scheduler
    if _scheduler is not None:
        _scheduler.shutdown(wait=False)
        _scheduler = None


def _register(kind: str) -> TaskState:
    task_id = secrets.token_hex(8)
    state = TaskState(task_id=task_id, kind=kind)
    with _tasks_lock:
        _tasks[task_id] = state
    return state


def submit_scan(path: str) -> str:
    """Submit a local-scan job; returns the task id immediately."""
    state = _register("scan")
    _get_scheduler().add_job(_run_scan, args=[state.task_id, path], id=state.task_id)
    return state.task_id


def submit_scrape(query: str, limit: int) -> str:
    """Submit a scrape job; returns the task id immediately."""
    state = _register("scrape")
    _get_scheduler().add_job(_run_scrape, args=[state.task_id, query, limit], id=state.task_id)
    return state.task_id


def get_task(task_id: str) -> TaskState | None:
    with _tasks_lock:
        return _tasks.get(task_id)


def cancel_task(task_id: str) -> bool:
    """Request cancellation. The worker checks ``cancel_requested`` and exits.
    Returns True if the task exists and was running/pending."""
    with _tasks_lock:
        state = _tasks.get(task_id)
    if state is None:
        return False
    if state.status in ("completed", "failed", "cancelled"):
        return False
    state.cancel_requested = True
    return True


def _is_cancelled(task_id: str) -> bool:
    with _tasks_lock:
        state = _tasks.get(task_id)
    return state is not None and state.cancel_requested


def _run_scan(task_id: str, path: str) -> None:
    """Worker: local scan. Imports lazily to avoid a circular import
    (import_service imports tasks for the cancel check)."""
    from app.services import import_service
    from app.db import SessionLocal

    with _tasks_lock:
        state = _tasks.get(task_id)
    if state is None:
        return
    state.status = "running"
    db = SessionLocal()
    try:
        import_service.scan_directory(task_id, path, state, _is_cancelled, db)
    except Exception as exc:  # pragma: no cover - defensive
        state.status = "failed"
        state.error = str(exc)
        state.finished_at = _now()
        return
    finally:
        db.close()
    state.status = "cancelled" if state.cancel_requested else "completed"
    state.finished_at = _now()


def _run_scrape(task_id: str, query: str, limit: int) -> None:
    """Worker: scrape. Cloudflare 403 means real Danbooru is unreachable; the
    job still runs and will report failure if the scraper can't connect."""
    from app.db import SessionLocal
    from app.scrapers.danbooru import DanbooruScraper
    from app.services import scrape as scrape_svc

    with _tasks_lock:
        state = _tasks.get(task_id)
    if state is None:
        return
    state.status = "running"
    db = SessionLocal()
    try:
        scraper = DanbooruScraper()
        result = scrape_svc.scrape_to_db(db, scraper, query, limit=limit)
        state.processed = state.total = result.new + result.duplicate + result.failed
        state.duplicates = result.duplicate
        state.failed = result.failed
    except Exception as exc:
        state.status = "failed"
        state.error = str(exc)
        state.finished_at = _now()
        return
    finally:
        db.close()
    state.status = "cancelled" if state.cancel_requested else "completed"
    state.finished_at = _now()
