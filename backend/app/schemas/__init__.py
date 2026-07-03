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
from app.schemas.tag import (
    TagCreateRequest,
    TagListResponse,
    TagTreeNode,
    TagTreeResponse,
    TagUpdateRequest,
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
    "TagCreateRequest",
    "TagListResponse",
    "TagResponse",
    "TagTreeNode",
    "TagTreeResponse",
    "TagUpdateRequest",
    "UpdateSettingsRequest",
    "UserResponse",
]
