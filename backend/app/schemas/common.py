"""Shared response schemas."""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class Envelope(BaseModel):
    """Success envelope: {"data": ..., "meta": {...}}."""

    data: Any
    meta: dict[str, Any] = Field(default_factory=dict)


class ErrorDetail(BaseModel):
    code: str
    message: str


class ErrorResponse(BaseModel):
    """Error envelope: {"error": {"code", "message"}}."""

    error: ErrorDetail
