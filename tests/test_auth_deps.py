"""Service token auth tests (M1 · PR-3)."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.config import get_settings
from app.main import app

TOKEN = "test-service-token"
ACTOR = "zhangsan"


def test_auth_check_ok(tmp_cservice_db, monkeypatch):
    monkeypatch.setenv("CSERVICE_SERVICE_TOKEN", TOKEN)
    get_settings.cache_clear()

    client = TestClient(app)
    r = client.get(
        "/api/v1/cservice/_internal/auth-check",
        headers={
            "Authorization": f"Bearer {TOKEN}",
            "X-Skstudio-User-Id": ACTOR,
        },
    )
    assert r.status_code == 200
    assert r.json() == {"ok": True, "actor": ACTOR}


def test_auth_check_invalid_token(tmp_cservice_db, monkeypatch):
    monkeypatch.setenv("CSERVICE_SERVICE_TOKEN", TOKEN)
    get_settings.cache_clear()

    client = TestClient(app)
    r = client.get(
        "/api/v1/cservice/_internal/auth-check",
        headers={
            "Authorization": "Bearer wrong-token",
            "X-Skstudio-User-Id": ACTOR,
        },
    )
    assert r.status_code == 401


def test_auth_check_missing_actor(tmp_cservice_db, monkeypatch):
    monkeypatch.setenv("CSERVICE_SERVICE_TOKEN", TOKEN)
    get_settings.cache_clear()

    client = TestClient(app)
    r = client.get(
        "/api/v1/cservice/_internal/auth-check",
        headers={"Authorization": f"Bearer {TOKEN}"},
    )
    assert r.status_code == 400


def test_auth_check_token_not_configured(tmp_cservice_db, monkeypatch):
    monkeypatch.setenv("CSERVICE_SERVICE_TOKEN", "")
    get_settings.cache_clear()

    client = TestClient(app)
    r = client.get(
        "/api/v1/cservice/_internal/auth-check",
        headers={
            "Authorization": "Bearer anything",
            "X-Skstudio-User-Id": ACTOR,
        },
    )
    assert r.status_code == 503
