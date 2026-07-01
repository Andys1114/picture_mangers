"""Pydantic schemas package."""
from app.schemas.auth import (
    LoginRequest,
    MeResponse,
    SetupRequest,
    StatusResponse,
    UpdateSettingsRequest,
    UserResponse,
)
from app.schemas.common import Envelope, ErrorDetail, ErrorResponse
from app.schemas.post import (
    PageMeta,
    PostDetailResponse,
    PostListResponse,
    PostSummaryResponse,
    TagResponse,
)

__all__ = [
    "Envelope",
    "ErrorDetail",
    "ErrorResponse",
    "LoginRequest",
    "MeResponse",
    "PageMeta",
    "PostDetailResponse",
    "PostListResponse",
    "PostSummaryResponse",
    "SetupRequest",
    "StatusResponse",
    "TagResponse",
    "UpdateSettingsRequest",
    "UserResponse",
]
