"""Auth service: password hashing and DB-backed session management.

Sessions are stored in the `sessions` table (not JWT) so logout can invalidate
immediately by deleting the row.
"""
from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone

import bcrypt
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import settings
from app.models.user import Session as SessionRow, User
from app.services.errors import ConflictError

_BCRYPT_COST = 12

SESSION_COOKIE = "gallery_session"


def hash_password(password: str) -> str:
    """Return a bcrypt hash. Stored as a UTF-8 str."""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(_BCRYPT_COST)).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))


def create_session(db: Session, user: User) -> str:
    """Issue a random token, persist a session row, return the token.

    New sessions default to safe_mode=True (server-authoritative; the gallery
    main view injects rating=safe while this is on).
    """
    token = secrets.token_urlsafe(32)
    expires_at = datetime.now(timezone.utc) + timedelta(days=settings.session_expire_days)
    db.add(
        SessionRow(
            id=token,
            user_id=user.id,
            expires_at=expires_at.replace(tzinfo=None),  # SQLite stores naive datetimes
            safe_mode=True,
        )
    )
    db.commit()
    return token


def get_session_row(db: Session, token: str | None) -> SessionRow | None:
    """Return the live session row for a token, or None.

    Unlike validate_session (which returns the User), this returns the row so
    callers can read/modify per-session fields like safe_mode. Expired/missing
    tokens resolve to None; expired rows are deleted on sight so the sessions
    table does not accumulate stale tokens.
    """
    if not token:
        return None
    row = db.get(SessionRow, token)
    if row is None:
        return None
    # Naive datetimes are interpreted as UTC.
    if row.expires_at <= datetime.utcnow():
        db.delete(row)
        db.commit()
        return None
    return row


def validate_session(db: Session, token: str | None) -> User | None:
    """Resolve a token to a User. Returns None if missing, expired, or unknown.

    Expired rows are deleted on sight (same cleanup as get_session_row).
    """
    if not token:
        return None
    row = db.get(SessionRow, token)
    if row is None:
        return None
    # Naive datetimes are interpreted as UTC.
    now = datetime.utcnow()
    if row.expires_at <= now:
        db.delete(row)
        db.commit()
        return None
    user = db.get(User, row.user_id)
    return user


def set_safe_mode(db: Session, session_row: SessionRow, value: bool) -> SessionRow:
    """Persist a session's safe_mode toggle (server-authoritative)."""
    session_row.safe_mode = value
    db.add(session_row)
    db.commit()
    db.refresh(session_row)
    return session_row


def delete_session(db: Session, token: str | None) -> None:
    """Invalidate a session (logout)."""
    if not token:
        return
    row = db.get(SessionRow, token)
    if row is not None:
        db.delete(row)
        db.commit()


def has_user(db: Session) -> bool:
    """True if any user exists (drives the setup_required flag)."""
    return db.execute(select(User.id).limit(1)).first() is not None


def create_user(db: Session, username: str, password: str) -> User:
    """Create the single application user.

    The id is pinned to 1 so a concurrent second setup collides on the
    primary key instead of racing past the caller's has_user() check.
    """
    user = User(id=1, username=username, password_hash=hash_password(password))
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise ConflictError("用户已存在,请直接登录")
    db.refresh(user)
    return user


def authenticate(db: Session, username: str, password: str) -> User | None:
    """Verify credentials. Returns the User or None."""
    user = db.execute(select(User).where(User.username == username)).scalar_one_or_none()
    if user is None or not verify_password(password, user.password_hash):
        return None
    return user
