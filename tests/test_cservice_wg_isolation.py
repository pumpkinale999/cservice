"""Channel isolation — wg ingress must not touch kf tables (CS-31)."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.config import get_settings
from app.db import get_session_factory
from app.main import app
from app.models import AgentThread, Message
from tests.conftest import load_json_fixture

TOKEN = "test-service-token"
HEADERS = {"Authorization": f"Bearer {TOKEN}"}
INGRESS_URL = "/api/v1/cservice/_internal/wecom-group/ingress"


def test_ingress_does_not_write_kf_tables_cs31(tmp_cservice_db, monkeypatch):
    monkeypatch.setenv("CSERVICE_SERVICE_TOKEN", TOKEN)
    monkeypatch.setenv("CSERVICE_WG_ENABLED", "1")
    get_settings.cache_clear()

    factory = get_session_factory()
    db = factory()
    try:
        msg_before = db.query(Message).count()
        thread_before = db.query(AgentThread).count()
    finally:
        db.close()

    payload = load_json_fixture("wg_ingress_text.json")
    client = TestClient(app)
    r = client.post(INGRESS_URL, json=payload, headers=HEADERS)
    assert r.status_code == 200

    db = factory()
    try:
        assert db.query(Message).count() == msg_before
        assert db.query(AgentThread).count() == thread_before
    finally:
        db.close()
