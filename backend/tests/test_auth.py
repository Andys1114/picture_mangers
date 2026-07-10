"""AC3-AC8, AC12 — auth state machine.

Covers: setup_required flag, /setup creation + 409 on second, login ok/fail,
me with/without cookie, logout, expired-session rejection; plus audit-fix
regressions (setup race, cookie max_age, safe_mode service, expired-row
cleanup, 72-byte password bound, login logging, Session alias hygiene).
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from app import db as db_module
from app.config import settings
from app.models.user import Session as SessionRow
from app.services import auth as auth_service
from app.services.errors import ConflictError


def _setup_user(client: TestClient) -> dict:
    return client.post(
        "/api/auth/setup",
        json={"username": "admin", "password": "pw12345678"},
    ).json()


def test_status_requires_setup(client: TestClient) -> None:
    """AC3: empty DB reports setup_required=true."""
    r = client.get("/api/auth/status")
    assert r.status_code == 200
    assert r.json() == {"setup_required": True}


def test_setup_creates_user_and_clears_flag(client: TestClient) -> None:
    """AC4: setup creates the user and flips setup_required to false."""
    r = client.post("/api/auth/setup", json={"username": "admin", "password": "pw12345678"})
    assert r.status_code == 201  # audit #20: creation returns 201
    assert r.json() == {"id": 1, "username": "admin"}
    assert "gallery_session" in r.cookies
    status = client.get("/api/auth/status").json()
    assert status == {"setup_required": False}


def test_setup_conflict_when_user_exists(client: TestClient) -> None:
    """AC5: a second setup attempt is rejected with 409."""
    _setup_user(client)
    r = client.post("/api/auth/setup", json={"username": "x", "password": "pw12345678"})
    assert r.status_code == 409
    assert r.json()["error"]["code"] == "conflict"


def test_login_success_and_wrong_password(client: TestClient) -> None:
    """AC6: correct credentials return 200 + cookie; wrong return 401."""
    _setup_user(client)
    # fresh client without the setup cookie
    from fastapi.testclient import TestClient as _TC

    anon = _TC(client.app)
    ok = anon.post("/api/auth/login", json={"username": "admin", "password": "pw12345678"})
    assert ok.status_code == 200
    assert ok.json()["username"] == "admin"
    assert "gallery_session" in ok.cookies

    bad = anon.post("/api/auth/login", json={"username": "admin", "password": "wrong"})
    assert bad.status_code == 401
    assert bad.json()["error"]["code"] == "unauthorized"


def test_me_with_and_without_cookie(client: TestClient) -> None:
    """AC7: /me returns the user with cookie, 401 without."""
    _setup_user(client)
    # with the setup cookie present
    r = client.get("/api/auth/me")
    assert r.status_code == 200
    assert r.json()["username"] == "admin"

    # without cookie
    from fastapi.testclient import TestClient as _TC

    anon = _TC(client.app)
    r = anon.get("/api/auth/me")
    assert r.status_code == 401


def test_logout_invalidates_cookie(client: TestClient) -> None:
    """AC8: after logout the old cookie no longer authenticates."""
    _setup_user(client)
    # confirm logged in
    assert client.get("/api/auth/me").status_code == 200
    r = client.post("/api/auth/logout")
    assert r.status_code == 204
    # the cookie is cleared on the client; re-asking /me with the cleared jar
    assert client.get("/api/auth/me").status_code == 401


def test_expired_session_rejected(client: TestClient) -> None:
    """AC12: a session whose expires_at is in the past is treated as invalid."""
    _setup_user(client)
    token = client.cookies["gallery_session"]
    # Force the row into the past.
    with db_module.SessionLocal() as db:
        row = db.get(SessionRow, token)
        assert row is not None
        row.expires_at = datetime.utcnow() - timedelta(days=1)
        db.commit()
    # Re-issue a request carrying the (now expired) cookie.
    from fastapi.testclient import TestClient as _TC

    holder = _TC(client.app)
    holder.cookies.set("gallery_session", token)
    r = holder.get("/api/auth/me")
    assert r.status_code == 401


def test_create_user_race_closed_by_fixed_id(client: TestClient) -> None:
    """audit #18: create_user pins id=1, so a second INSERT — even with a
    different username, bypassing the route's has_user() check — hits the
    primary key and surfaces as ConflictError (409)."""
    _setup_user(client)
    with db_module.SessionLocal() as db:
        with pytest.raises(ConflictError):
            auth_service.create_user(db, "other", "pw12345678")
        # the session was rolled back and stays usable
        assert auth_service.has_user(db) is True


def test_session_cookie_carries_max_age(client: TestClient) -> None:
    """audit #19: setup/login cookies get a max_age matching the server-side
    session expiry (session_expire_days)."""
    expected = f"max-age={settings.session_expire_days * 86400}"
    r = client.post("/api/auth/setup", json={"username": "admin", "password": "pw12345678"})
    assert expected in r.headers["set-cookie"].lower()

    anon = TestClient(client.app)
    ok = anon.post("/api/auth/login", json={"username": "admin", "password": "pw12345678"})
    assert expected in ok.headers["set-cookie"].lower()


def test_update_settings_persists_safe_mode(client: TestClient) -> None:
    """audit #21: safe_mode toggling goes through the service layer and
    persists across requests."""
    _setup_user(client)
    r = client.patch("/api/auth/me/settings", json={"safe_mode": False})
    assert r.status_code == 200
    assert r.json()["safe_mode"] is False
    assert client.get("/api/auth/me").json()["safe_mode"] is False

    # the service function is callable outside HTTP too
    token = client.cookies["gallery_session"]
    with db_module.SessionLocal() as db:
        row = db.get(SessionRow, token)
        updated = auth_service.set_safe_mode(db, row, True)
        assert updated.safe_mode is True
    assert client.get("/api/auth/me").json()["safe_mode"] is True


def test_expired_session_row_deleted_on_access(client: TestClient) -> None:
    """audit #22: an expired session row is physically deleted when touched,
    both via get_session_row (deps path) and validate_session."""
    _setup_user(client)
    token = client.cookies["gallery_session"]
    with db_module.SessionLocal() as db:
        row = db.get(SessionRow, token)
        row.expires_at = datetime.utcnow() - timedelta(days=1)
        db.commit()

    holder = TestClient(client.app)
    holder.cookies.set("gallery_session", token)
    assert holder.get("/api/auth/me").status_code == 401
    with db_module.SessionLocal() as db:
        assert db.get(SessionRow, token) is None

    # validate_session cleans up too
    anon = TestClient(client.app)
    ok = anon.post("/api/auth/login", json={"username": "admin", "password": "pw12345678"})
    token2 = ok.cookies["gallery_session"]
    with db_module.SessionLocal() as db:
        row = db.get(SessionRow, token2)
        row.expires_at = datetime.utcnow() - timedelta(days=1)
        db.commit()
    with db_module.SessionLocal() as db:
        assert auth_service.validate_session(db, token2) is None
        assert db.get(SessionRow, token2) is None


def test_password_over_72_bytes_rejected(client: TestClient) -> None:
    """audit #23: passwords longer than 72 UTF-8 bytes are rejected with 422
    on both setup and login (bcrypt would silently truncate them)."""
    r = client.post("/api/auth/setup", json={"username": "admin", "password": "a" * 73})
    assert r.status_code == 422
    # byte count, not char count: 25 CJK chars = 75 bytes
    r = client.post("/api/auth/setup", json={"username": "admin", "password": "密" * 25})
    assert r.status_code == 422
    # no user was created by the rejected attempts
    assert client.get("/api/auth/status").json() == {"setup_required": True}

    _setup_user(client)
    r = client.post("/api/auth/login", json={"username": "admin", "password": "a" * 73})
    assert r.status_code == 422
    # exactly 72 bytes passes validation (fails auth, not validation)
    r = client.post("/api/auth/login", json={"username": "admin", "password": "a" * 72})
    assert r.status_code == 401


def test_login_success_and_failure_logged(client: TestClient, caplog) -> None:
    """audit #39: login success/failure emit INFO logs with the username but
    never the password."""
    _setup_user(client)
    anon = TestClient(client.app)
    with caplog.at_level(logging.INFO, logger="app.api.auth"):
        anon.post("/api/auth/login", json={"username": "admin", "password": "pw12345678"})
        anon.post("/api/auth/login", json={"username": "admin", "password": "wrong-pass"})
    messages = [rec.getMessage() for rec in caplog.records]
    assert any("login success username=admin" in m for m in messages)
    assert any("login failed username=admin" in m for m in messages)
    assert not any("pw12345678" in m or "wrong-pass" in m for m in messages)


def test_orm_session_alias_not_shadowed() -> None:
    """audit #40: `Session` in deps/api.auth must be sqlalchemy.orm.Session;
    the sessions-table model is aliased as SessionRow."""
    import sqlalchemy.orm

    from app import deps
    from app.api import auth as auth_api

    assert deps.Session is sqlalchemy.orm.Session
    assert auth_api.Session is sqlalchemy.orm.Session
    assert deps.SessionRow.__tablename__ == "sessions"
    assert auth_api.SessionRow.__tablename__ == "sessions"
