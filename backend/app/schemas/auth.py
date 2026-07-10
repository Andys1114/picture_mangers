"""Auth request/response schemas."""
from __future__ import annotations

from pydantic import BaseModel, Field, field_validator

# bcrypt only hashes the first 72 bytes of a password; anything longer would
# be silently truncated at hash/verify time, so reject it up front.
_BCRYPT_MAX_PASSWORD_BYTES = 72


def _check_password_bytes(value: str) -> str:
    if len(value.encode("utf-8")) > _BCRYPT_MAX_PASSWORD_BYTES:
        raise ValueError("密码过长：最多 72 字节")
    return value


class SetupRequest(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=8, max_length=128)

    @field_validator("password")
    @classmethod
    def _password_fits_bcrypt(cls, value: str) -> str:
        return _check_password_bytes(value)


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=128)

    @field_validator("password")
    @classmethod
    def _password_fits_bcrypt(cls, value: str) -> str:
        return _check_password_bytes(value)


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
