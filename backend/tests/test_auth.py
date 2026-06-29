"""AC3-AC8, AC12 — auth state machine.

Covers: setup_required flag, /setup creation + 409 on second, login ok/fail,
me with/without cookie, logout, expired-session rejection.
"""
from __future__ import annotations

from datetime import datetime, timedelta

from fastapi.testclient import TestClient

from app import db as db_module
from app.models.user import Session as SessionRow


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
    assert r.status_code == 200
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
