"""Auth service: password hashing and DB-backed session management.

Sessions are stored in the `sessions` table (not JWT) so logout can invalidate
immediately by deleting the row.
"""
from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone

import bcrypt
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.models.user import Session as SessionRow, User

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
    tokens resolve to None.
    """
    if not token:
        return None
    row = db.get(SessionRow, token)
    if row is None:
        return None
    # Naive datetimes are interpreted as UTC.
    if row.expires_at <= datetime.utcnow():
        return None
    return row


def validate_session(db: Session, token: str | None) -> User | None:
    """Resolve a token to a User. Returns None if missing, expired, or unknown."""
    if not token:
        return None
    row = db.get(SessionRow, token)
    if row is None:
        return None
    # Naive datetimes are interpreted as UTC.
    now = datetime.utcnow()
    if row.expires_at <= now:
        return None
    user = db.get(User, row.user_id)
    return user


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
    """Create the single application user."""
    user = User(username=username, password_hash=hash_password(password))
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def authenticate(db: Session, username: str, password: str) -> User | None:
    """Verify credentials. Returns the User or None."""
    user = db.execute(select(User).where(User.username == username)).scalar_one_or_none()
    if user is None or not verify_password(password, user.password_hash):
        return None
    return user
