"""Multi-@ merge round tests (CS-39 · D-P4-15)."""

from __future__ import annotations

import json

from fastapi.testclient import TestClient

from app.config import get_settings
from app.db import get_session_factory
from app.main import app
from app.models import WgAgentThread, WgDraft
from tests.conftest import load_json_fixture
from tests.wg_helpers import HEADERS, INGRESS_URL, TOKEN


def test_wg_merge_round_one_pending_draft(tmp_cservice_db, monkeypatch):
    """Two consecutive @ in same round → supersede + one pending draft."""
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

        payload_a = load_json_fixture("wg_ingress_text.json")
        r1 = client.post(INGRESS_URL, json=payload_a, headers=HEADERS)
        assert r1.status_code == 200
        uplink_a = json.loads(ws.receive_text())
        assert uplink_a["type"] == "cservice_group_uplink"

        ws.send_json(
            {
                "type": "cservice_draft_reply",
                "thread_id": uplink_a["thread_id"],
                "session_id": uplink_a["session_id"],
                "body": "draft for A",
                "stream_status": "final",
                "trigger_source_msgid": payload_a["msgid"],
            }
        )
        ws.receive_text()

        payload_b = {
            **payload_a,
            "msgid": "msg_wg_002",
            "sender_userid": "user_bob",
            "text": "@数坤坤健康助手 还有别的建议吗？",
            "response_url": "https://example.com/new-url",
        }
        r2 = client.post(INGRESS_URL, json=payload_b, headers=HEADERS)
        assert r2.status_code == 200
        uplink_b = json.loads(ws.receive_text())
        assert "还有别的建议吗？" in uplink_b["body"]
        assert "请问体检报告怎么看？" in uplink_b["body"]

        ws.send_json(
            {
                "type": "cservice_draft_reply",
                "thread_id": uplink_b["thread_id"],
                "session_id": uplink_b["session_id"],
                "body": "merged draft",
                "stream_status": "final",
                "trigger_source_msgid": payload_b["msgid"],
            }
        )
        ws.receive_text()

    factory = get_session_factory()
    db = factory()
    try:
        session_id = r1.json()["session_id"]
        pending = (
            db.query(WgDraft)
            .filter_by(session_id=session_id, status="pending")
            .all()
        )
        assert len(pending) == 1
        assert pending[0].agent_text == "merged draft"
        superseded = (
            db.query(WgDraft)
            .filter_by(session_id=session_id, status="superseded")
            .count()
        )
        assert superseded == 1
        assert db.query(WgAgentThread).count() == 1
    finally:
        db.close()
