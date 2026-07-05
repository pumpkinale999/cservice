"""Uplink enqueue tests (M3 · PR-3)."""

from __future__ import annotations

import json

from fastapi.testclient import TestClient

from app.db import get_session_factory
from app.hermes.uplink_queue import enqueue_uplink
from app.main import app
from app.models import UplinkRetry
from app.services.sync_pipeline import run_sync_for_kf
from app.services.uplink_hook import HermesUplinkHook
from tests.conftest import build_mock_wecom_client, load_json_fixture


def test_uplink_enqueued_when_gateway_connected(loaded_seed, wecom_env, monkeypatch):
    monkeypatch.setenv("CSERVICE_SERVICE_TOKEN", "tok")
    from app.config import get_settings

    get_settings.cache_clear()
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
        mock = build_mock_wecom_client(
            sync_responses=[load_json_fixture("sync_msg_text_inbound.json")]
        )
        factory = get_session_factory()
        db = factory()
        try:
            run_sync_for_kf(
                db,
                "wkTEST_MINIMAL",
                token="T1",
                client=mock,
                uplink_hook=HermesUplinkHook(),
            )
        finally:
            db.close()
        msg = json.loads(ws.receive_text())
        assert msg["type"] == "cservice_customer_uplink"
        assert msg["trigger_wx_msgid"] == "msg_inbound_001"


def test_uplink_retry_when_offline(loaded_seed, wecom_env):
    factory = get_session_factory()
    db = factory()
    try:
        enqueue_uplink(
            db,
            session_id="sess-1",
            thread_id=1,
            open_kfid="wkTEST_MINIMAL",
            external_userid="wmTEST001",
            text="hi",
            trigger_wx_msgid="m1",
        )
        db.commit()
        assert db.query(UplinkRetry).count() == 1
    finally:
        db.close()
