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
from app.schemas.favorite import (
    FavoriteCreateRequest,
    FavoriteDetailResponse,
    FavoriteItemReorderRequest,
    FavoriteItemResponse,
    FavoriteResponse,
    StarToggleResponse,
)
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
from app.schemas.task import (
    ScanRequest,
    ScrapeRequest,
    TaskCancelResponse,
    TaskCreateResponse,
    TaskStatusResponse,
)

__all__ = [
    "Envelope",
    "ErrorDetail",
    "ErrorResponse",
    "FavoriteCreateRequest",
    "FavoriteDetailResponse",
    "FavoriteItemReorderRequest",
    "FavoriteItemResponse",
    "FavoriteResponse",
    "LoginRequest",
    "MeResponse",
    "PageMeta",
    "PostDetailResponse",
    "PostListResponse",
    "PostSummaryResponse",
    "ScanRequest",
    "ScrapeRequest",
    "SetupRequest",
    "StarToggleResponse",
    "StatusResponse",
    "TagCreateRequest",
    "TaskCancelResponse",
    "TaskCreateResponse",
    "TaskStatusResponse",
    "TagListResponse",
    "TagResponse",
    "TagTreeNode",
    "TagTreeResponse",
    "TagUpdateRequest",
    "UpdateSettingsRequest",
    "UserResponse",
]
