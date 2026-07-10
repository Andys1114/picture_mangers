"""Auth routes: status, setup, login, logout, me.

State machine (see design.md section 2):
- DB has no user  -> setup_required=true, /setup creates the single user.
- /login issues a DB-backed session via the gallery_session cookie.
- /me requires a valid session; /logout deletes the session row.
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, Request, Response, status
from sqlalchemy.orm import Session

from app.config import settings
from app.db import get_db
from app.deps import get_current_session
from app.models.user import Session as SessionRow
from app.schemas.auth import (
    LoginRequest,
    MeResponse,
    SetupRequest,
    StatusResponse,
    UpdateSettingsRequest,
    UserResponse,
)
from app.services import auth
from app.services.errors import ConflictError, UnauthorizedError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])

_COOKIE_KWARGS = {
    "key": auth.SESSION_COOKIE,
    "httponly": True,
    "samesite": "lax",
    "secure": settings.secure_cookie,
    "path": "/",
    # Keep the cookie lifetime aligned with the server-side session expiry.
    "max_age": settings.session_expire_days * 86400,
}


@router.get("/status", response_model=StatusResponse)
def get_status(db: Session = Depends(get_db)) -> StatusResponse:
    """Tell the client whether the /setup wizard is needed."""
    return StatusResponse(setup_required=not auth.has_user(db))


@router.post("/setup", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def setup(payload: SetupRequest, response: Response, db: Session = Depends(get_db)) -> UserResponse:
    """First-run user creation. Only works when no user exists yet."""
    if auth.has_user(db):
        raise ConflictError("用户已存在,请直接登录")
    user = auth.create_user(db, payload.username, payload.password)
    token = auth.create_session(db, user)
    response.set_cookie(value=token, **_COOKIE_KWARGS)
    logger.info("setup completed username=%s", user.username)
    return UserResponse(id=user.id, username=user.username)


@router.post("/login", response_model=UserResponse)
def login(payload: LoginRequest, response: Response, db: Session = Depends(get_db)) -> UserResponse:
    """Verify credentials and issue a session cookie."""
    user = auth.authenticate(db, payload.username, payload.password)
    if user is None:
        logger.info("login failed username=%s", payload.username)
        raise UnauthorizedError("用户名或密码错误")
    token = auth.create_session(db, user)
    response.set_cookie(value=token, **_COOKIE_KWARGS)
    logger.info("login success username=%s", user.username)
    return UserResponse(id=user.id, username=user.username)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(request: Request, response: Response, db: Session = Depends(get_db)) -> None:
    """Delete the current session row and clear the cookie."""
    token = request.cookies.get(auth.SESSION_COOKIE)
    auth.delete_session(db, token)
    response.delete_cookie(key=auth.SESSION_COOKIE, path="/")
    logger.info("logout")


@router.get("/me", response_model=MeResponse)
def me(session: SessionRow = Depends(get_current_session)) -> MeResponse:
    """Current user + per-session safe_mode. Requires a valid session cookie."""
    user = session.user
    return MeResponse(id=user.id, username=user.username, safe_mode=session.safe_mode)


@router.patch("/me/settings", response_model=MeResponse)
def update_settings(
    payload: UpdateSettingsRequest,
    session: SessionRow = Depends(get_current_session),
    db: Session = Depends(get_db),
) -> MeResponse:
    """Toggle the current session's safe_mode (server-authoritative).

    The gallery main view injects rating=safe while safe_mode is on; toggling
    invalidates the posts list on the client so it refetches with the new filter.
    """
    session = auth.set_safe_mode(db, session, payload.safe_mode)
    user = session.user
    return MeResponse(id=user.id, username=user.username, safe_mode=session.safe_mode)
