"""Auth request/response schemas."""
from __future__ import annotations

from pydantic import BaseModel, Field


class SetupRequest(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=8, max_length=128)


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=128)


class UserResponse(BaseModel):
    id: int
    username: str


class MeResponse(BaseModel):
    """Current user + per-session safe_mode (returned by /me)."""

    id: int
    username: str
    safe_mode: bool


class UpdateSettingsRequest(BaseModel):
    """PATCH /me/settings body — toggle the current session's safe_mode."""

    safe_mode: bool


class StatusResponse(BaseModel):
    setup_required: bool
