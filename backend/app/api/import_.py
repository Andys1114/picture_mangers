"""Import/task routes: scan, scrape, task status, cancel.

Thin handlers delegating to app.services.tasks. All require auth. The module
is named ``import_`` (trailing underscore) to avoid the Python ``import``
keyword. Mounted under /api/import + /api/tasks.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_current_user
from app.models.user import User
from app.schemas.task import (
    ScanRequest,
    ScrapeRequest,
    TaskCancelResponse,
    TaskCreateResponse,
    TaskStatusResponse,
)
from app.services import tasks
from app.services.errors import NotFoundError

router = APIRouter(tags=["import"])


def _to_status(state: tasks.TaskState) -> TaskStatusResponse:
    return TaskStatusResponse(
        task_id=state.task_id,
        kind=state.kind,
        status=state.status,
        processed=state.processed,
        total=state.total,
        duplicates=state.duplicates,
        failed=state.failed,
        error=state.error,
    )


@router.post("/import/scan", response_model=TaskCreateResponse, status_code=status.HTTP_201_CREATED)
def submit_scan(
    payload: ScanRequest,
    _user: User = Depends(get_current_user),
    _db: Session = Depends(get_db),
) -> TaskCreateResponse:
    """Start a local-folder scan; returns the task id immediately."""
    task_id = tasks.submit_scan(payload.path)
    return TaskCreateResponse(task_id=task_id)


@router.post("/import/scrape", response_model=TaskCreateResponse, status_code=status.HTTP_201_CREATED)
def submit_scrape(
    payload: ScrapeRequest,
    _user: User = Depends(get_current_user),
    _db: Session = Depends(get_db),
) -> TaskCreateResponse:
    """Start a scrape job; returns the task id immediately."""
    task_id = tasks.submit_scrape(payload.query, payload.limit)
    return TaskCreateResponse(task_id=task_id)


@router.get("/tasks/{task_id}", response_model=TaskStatusResponse)
def get_task(
    task_id: str,
    _user: User = Depends(get_current_user),
    _db: Session = Depends(get_db),
) -> TaskStatusResponse:
    """Poll a task's progress."""
    state = tasks.get_task(task_id)
    if state is None:
        raise NotFoundError("任务不存在")
    return _to_status(state)


@router.post("/tasks/{task_id}/cancel", response_model=TaskCancelResponse)
def cancel_task(
    task_id: str,
    _user: User = Depends(get_current_user),
    _db: Session = Depends(get_db),
) -> TaskCancelResponse:
    """Request cancellation of a running/pending task."""
    cancelled = tasks.cancel_task(task_id)
    return TaskCancelResponse(cancelled=cancelled)
