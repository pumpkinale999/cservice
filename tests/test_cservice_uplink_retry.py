"""Uplink retry flush (M3 · PR-3)."""

from __future__ import annotations

import json

from fastapi.testclient import TestClient

from app.db import get_session_factory
from app.hermes.uplink_queue import enqueue_uplink
from app.main import app
from app.models import UplinkRetry


def test_flush_on_register(loaded_seed, monkeypatch):
    monkeypatch.setenv("CSERVICE_SERVICE_TOKEN", "tok")
    from app.config import get_settings

    get_settings.cache_clear()
    factory = get_session_factory()
    db = factory()
    try:
        enqueue_uplink(
            db,
            session_id="sess-flush",
            thread_id=2,
            open_kfid="wkTEST_MINIMAL",
            external_userid="wmTEST001",
            text="retry me",
            trigger_wx_msgid="m_retry",
        )
        db.commit()
        assert db.query(UplinkRetry).count() == 1
    finally:
        db.close()

    client = TestClient(app)
    with client.websocket_connect(
        "/ws/hermes",
        headers={"Authorization": "Bearer tok"},
    ) as ws:
        ws.send_json(
            {
                "type": "gateway_register",
                "gateway_role": "cservice",
                "agent_slug": "cservice-assistant",
            }
        )
        ws.receive_text()
        uplink = json.loads(ws.receive_text())
        assert uplink["type"] == "cservice_customer_uplink"
    db2 = factory()
    try:
        assert db2.query(UplinkRetry).count() == 0
    finally:
        db2.close()
