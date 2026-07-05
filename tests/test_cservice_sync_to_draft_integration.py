"""Sync → uplink → downlink → draft integration."""

from __future__ import annotations

import json

from fastapi.testclient import TestClient

from app.db import get_session_factory
from app.main import app
from app.models import Draft
from app.services.kf_webhook_handler import handle_kf_event_plain
from app.services.sync_job import run_sync_job_now, set_sync_runner
from tests.conftest import build_mock_wecom_client, load_json_fixture

FIXTURES = __import__("pathlib").Path(__file__).resolve().parent / "fixtures" / "cservice"


def test_sync_to_draft_integration(loaded_seed, wecom_env, monkeypatch):
    monkeypatch.setenv("CSERVICE_SERVICE_TOKEN", "tok")
    from app.config import get_settings

    get_settings.cache_clear()
    downlink = load_json_fixture("draft_reply_downlink.json")

    http = TestClient(app)

    def run_sync(open_kfid: str, token: str | None) -> None:
        client_mock = build_mock_wecom_client(
            sync_responses=[load_json_fixture("sync_msg_text_inbound.json")]
        )
        run_sync_job_now(open_kfid, token, client_mock)

    set_sync_runner(run_sync)
    plain = (FIXTURES / "webhook_kf_msg_or_event.xml").read_text(encoding="utf-8")
    factory = get_session_factory()
    db = factory()
    try:
        assert handle_kf_event_plain(db, plain) is True
    finally:
        db.close()

    with http.websocket_connect(
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
        sid = uplink["session_id"]
        downlink["session_id"] = sid
        downlink["thread_id"] = uplink["thread_id"]
        downlink["trigger_wx_msgid"] = uplink["trigger_wx_msgid"]
        ws.send_json(downlink)
        ack = json.loads(ws.receive_text())
        assert ack["accepted"] is True

    db2 = factory()
    try:
        assert db2.query(Draft).filter_by(session_id=sid, status="pending").count() == 1
    finally:
        db2.close()
