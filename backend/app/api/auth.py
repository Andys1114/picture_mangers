"""Auth routes: status, setup, login, logout, me.

State machine (see design.md section 2):
- DB has no user  -> setup_required=true, /setup creates the single user.
- /login issues a DB-backed session via the gallery_session cookie.
- /me requires a valid session; /logout deletes the session row.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Request, Response, status
from sqlalchemy.orm import Session

from app.config import settings
from app.db import get_db
from app.deps import get_current_user
from app.models.user import User
from app.schemas.auth import (
    LoginRequest,
    SetupRequest,
    StatusResponse,
    UserResponse,
)
from app.services import auth
from app.services.errors import ConflictError, UnauthorizedError

router = APIRouter(prefix="/auth", tags=["auth"])

_COOKIE_KWARGS = {
    "key": auth.SESSION_COOKIE,
    "httponly": True,
    "samesite": "lax",
    "secure": settings.secure_cookie,
    "path": "/",
}


@router.get("/status", response_model=StatusResponse)
def get_status(db: Session = Depends(get_db)) -> StatusResponse:
    """Tell the client whether the /setup wizard is needed."""
    return StatusResponse(setup_required=not auth.has_user(db))


@router.post("/setup", response_model=UserResponse, status_code=status.HTTP_200_OK)
def setup(payload: SetupRequest, response: Response, db: Session = Depends(get_db)) -> UserResponse:
    """First-run user creation. Only works when no user exists yet."""
    if auth.has_user(db):
        raise ConflictError("用户已存在,请直接登录")
    user = auth.create_user(db, payload.username, payload.password)
    token = auth.create_session(db, user)
    response.set_cookie(value=token, **_COOKIE_KWARGS)
    return UserResponse(id=user.id, username=user.username)


@router.post("/login", response_model=UserResponse)
def login(payload: LoginRequest, response: Response, db: Session = Depends(get_db)) -> UserResponse:
    """Verify credentials and issue a session cookie."""
    user = auth.authenticate(db, payload.username, payload.password)
    if user is None:
        raise UnauthorizedError("用户名或密码错误")
    token = auth.create_session(db, user)
    response.set_cookie(value=token, **_COOKIE_KWARGS)
    return UserResponse(id=user.id, username=user.username)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(request: Request, response: Response, db: Session = Depends(get_db)) -> None:
    """Delete the current session row and clear the cookie."""
    token = request.cookies.get(auth.SESSION_COOKIE)
    auth.delete_session(db, token)
    response.delete_cookie(key=auth.SESSION_COOKIE, path="/")


@router.get("/me", response_model=UserResponse)
def me(user: User = Depends(get_current_user)) -> UserResponse:
    return UserResponse(id=user.id, username=user.username)
