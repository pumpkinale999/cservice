"""Ingress → uplink → downlink integration (P4-M2)."""

from __future__ import annotations

import json

from fastapi.testclient import TestClient

from app.config import get_settings
from app.db import get_session_factory
from app.main import app
from app.models import WgDraft
from tests.conftest import load_json_fixture
from tests.wg_helpers import HEADERS, INGRESS_URL, TOKEN


def test_ingress_to_draft_integration(tmp_cservice_db, monkeypatch):
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
        session_id = r.json()["session_id"]

        uplink = json.loads(ws.receive_text())
        assert uplink["type"] == "cservice_group_uplink"

        ws.send_json(
            {
                "type": "cservice_draft_reply",
                "thread_id": uplink["thread_id"],
                "session_id": session_id,
                "body": "集成测试回复",
                "stream_status": "final",
                "trigger_source_msgid": payload["msgid"],
            }
        )
        ack = json.loads(ws.receive_text())
        assert ack["accepted"] is True

    factory = get_session_factory()
    db = factory()
    try:
        draft = db.query(WgDraft).filter_by(session_id=session_id, status="pending").one()
        assert draft.agent_text == "集成测试回复"
    finally:
        db.close()
