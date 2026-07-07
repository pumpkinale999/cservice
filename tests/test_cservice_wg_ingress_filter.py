"""WeCom group ingress non-text filter tests (CS-40)."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.config import get_settings
from app.db import get_session_factory
from app.main import app
from app.models import WgMessage
from tests.conftest import load_json_fixture

TOKEN = "test-service-token"
HEADERS = {"Authorization": f"Bearer {TOKEN}"}
INGRESS_URL = "/api/v1/cservice/_internal/wecom-group/ingress"


def _enable_wg(monkeypatch) -> None:
    monkeypatch.setenv("CSERVICE_SERVICE_TOKEN", TOKEN)
    monkeypatch.setenv("CSERVICE_WG_ENABLED", "1")
    get_settings.cache_clear()


def test_ingress_ignores_image_cs40(tmp_cservice_db, monkeypatch):
    _enable_wg(monkeypatch)
    base = load_json_fixture("wg_ingress_text.json")
    payload = {
        **base,
        "msgid": "msg_image_001",
        "msgtype": "image",
        "text": "",
    }
    client = TestClient(app)
    r = client.post(INGRESS_URL, json=payload, headers=HEADERS)
    assert r.status_code == 200
    body = r.json()
    assert body["ignored"] is True
    assert body["reason"] == "non_text"

    factory = get_session_factory()
    db = factory()
    try:
        assert db.query(WgMessage).count() == 0
    finally:
        db.close()


def test_ingress_ignores_voice(tmp_cservice_db, monkeypatch):
    _enable_wg(monkeypatch)
    base = load_json_fixture("wg_ingress_text.json")
    payload = {
        **base,
        "msgid": "msg_voice_001",
        "msgtype": "voice",
        "text": "",
    }
    client = TestClient(app)
    r = client.post(INGRESS_URL, json=payload, headers=HEADERS)
    assert r.status_code == 200
    assert r.json()["ignored"] is True

    factory = get_session_factory()
    db = factory()
    try:
        assert db.query(WgMessage).count() == 0
    finally:
        db.close()


def test_ingress_ignores_empty_text(tmp_cservice_db, monkeypatch):
    _enable_wg(monkeypatch)
    base = load_json_fixture("wg_ingress_text.json")
    payload = {**base, "msgid": "msg_empty_001", "text": "   "}
    client = TestClient(app)
    r = client.post(INGRESS_URL, json=payload, headers=HEADERS)
    assert r.status_code == 200
    assert r.json()["ignored"] is True
