"""Local-import scan orchestration: recursive walk + mtime-incremental skip + ingest.

Walks a directory recursively, skipping files whose ``scan_history`` mtime
matches the current ``os.path.getmtime`` (already scanned, unchanged). New /
changed files are read into bytes and handed to ``media.ingest`` (which md5-
dedups and writes the Post). ``scan_history`` is updated after each ingest so a
re-scan skips it next time.

Local imports carry no tags (parent PRD F5) — tagging is a manual later action.
"""
from __future__ import annotations

import os
from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.scan_history import ScanHistory
from app.services import media
from app.services.errors import DuplicateError

if TYPE_CHECKING:
    from app.services.tasks import TaskState

# Supported local-import extensions (parent design.md §4).
SUPPORTED_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".apng"}

# Files larger than this are still ingested; the cap just guards against a
# pathological huge file stalling a single-threaded scan. 200 MB.
MAX_FILE_BYTES = 200 * 1024 * 1024


def scan_directory(
    task_id: str,
    root: str,
    state: "TaskState",
    is_cancelled: Callable[[str], bool],
    db: Session,
) -> None:
    """Recursively scan ``root`` for supported images, incrementally ingesting
    new/changed files and updating ``state`` progress as it goes.

    ``is_cancelled`` is polled each file; True aborts (the caller marks the
    task cancelled). ``db`` is the worker thread's own session.
    """
    files = sorted(
        p for p in _walk_files(root)
        if p.suffix.lower() in SUPPORTED_EXTS and p.stat().st_size <= MAX_FILE_BYTES
    )
    state.total = len(files)

    for p in files:
        if is_cancelled(task_id):
            return

        path_str = str(p)
        try:
            mtime = os.path.getmtime(path_str)
        except OSError:
            state.failed += 1
            state.processed += 1
            continue

        hist = db.execute(
            select(ScanHistory).where(ScanHistory.path == path_str)
        ).scalar_one_or_none()

        # Incremental skip: path seen + mtime unchanged.
        if hist is not None and hist.mtime == mtime:
            state.processed += 1
            continue

        try:
            data = p.read_bytes()
            ext = p.suffix.lower().lstrip(".")
            # GIF/APNG detection: media.ingest takes is_animated from caller;
            # animated gif if ext is gif (cheapest heuristic without decoding).
            is_animated = ext == "gif"
            media.ingest(
                db, data,
                source_site="local", source_id=None, source_url=None,
                file_ext=ext, is_animated=is_animated, rating="safe",
            )
        except DuplicateError:
            state.duplicates += 1
        except Exception:
            state.failed += 1
        else:
            # Record / update scan_history so the next scan can skip.
            if hist is not None:
                hist.mtime = mtime
            else:
                db.add(ScanHistory(path=path_str, mtime=mtime))
            db.commit()

        state.processed += 1


def _walk_files(root: str):
    """Yield Path objects for every regular file under ``root`` recursively."""
    root_path = Path(root)
    if not root_path.is_dir():
        return
    for dirpath, _dirnames, filenames in os.walk(root_path):
        for name in filenames:
            yield Path(dirpath) / name
