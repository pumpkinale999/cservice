"""WeCom group uplink enqueue tests (P4-M2)."""

from __future__ import annotations

import json

from fastapi.testclient import TestClient

from app.config import get_settings
from app.db import get_session_factory
from app.hermes.wg_uplink_queue import enqueue_wg_uplink
from app.main import app
from app.models import WgUplinkRetry
from tests.conftest import load_json_fixture
from tests.wg_helpers import HEADERS, INGRESS_URL, TOKEN, seed_wg_group_session


def test_wg_uplink_enqueued_when_group_gateway_connected(tmp_cservice_db, monkeypatch):
    monkeypatch.setenv("CSERVICE_SERVICE_TOKEN", TOKEN)
    monkeypatch.setenv("CSERVICE_WG_ENABLED", "1")
    get_settings.cache_clear()

    client = TestClient(app)
    with client.websocket_connect(
        "/ws/hermes",
        headers={"Authorization": f"Bearer {TOKEN}"},
    ) as ws:
        ws.send_json(
            {
                "type": "gateway_register",
                "gateway_role": "cservice-group",
                "agent_slug": "cservice-group-assistant",
            }
        )
        ws.receive_text()

        payload = load_json_fixture("wg_ingress_text.json")
        r = client.post(INGRESS_URL, json=payload, headers=HEADERS)
        assert r.status_code == 200

        msg = json.loads(ws.receive_text())
        assert msg["type"] == "cservice_group_uplink"
        assert msg["chatid"] == payload["chatid"]
        assert msg["trigger_source_msgid"] == payload["msgid"]
        assert "【本轮待回复】" in msg["body"]


def test_wg_uplink_retry_when_offline(tmp_cservice_db, monkeypatch):
    monkeypatch.setenv("CSERVICE_WG_ENABLED", "1")
    get_settings.cache_clear()
    factory = get_session_factory()
    db = factory()
    try:
        session, group = seed_wg_group_session(db)
        db.commit()
        enqueue_wg_uplink(
            db,
            session_id=session.id,
            thread_id=1,
            ibot_id=group.ibot_id,
            chatid=group.chatid,
            trigger_source_msgid="m1",
            sender_userid="user_a",
        )
        db.commit()
        assert db.query(WgUplinkRetry).count() == 1
    finally:
        db.close()
