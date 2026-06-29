"""FastAPI dependencies."""
from __future__ import annotations

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from app.db import get_db
from app.models.user import User
from app.services import auth
from app.services.errors import UnauthorizedError


def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    """Resolve the current user from the session cookie.

    Raises 401 (as an AppError) when no valid session is present.
    """
    token = request.cookies.get(auth.SESSION_COOKIE)
    user = auth.validate_session(db, token)
    if user is None:
        raise UnauthorizedError("未登录或会话已过期")
    return user
