"""Task (import/scrape) request/response schemas."""
from __future__ import annotations

from pydantic import BaseModel, Field


class ScanRequest(BaseModel):
    path: str = Field(min_length=1, max_length=1024)


class ScrapeRequest(BaseModel):
    query: str = Field(min_length=1, max_length=512)
    source: str = Field(default="danbooru", pattern=r"^danbooru$")
    limit: int = Field(default=20, ge=1, le=1000)


class TaskCreateResponse(BaseModel):
    task_id: str


class TaskStatusResponse(BaseModel):
    task_id: str
    kind: str  # "scan" | "scrape"
    status: str  # "pending" | "running" | "completed" | "failed" | "cancelled"
    processed: int
    total: int
    duplicates: int
    failed: int
    error: str | None = None


class TaskCancelResponse(BaseModel):
    cancelled: bool
