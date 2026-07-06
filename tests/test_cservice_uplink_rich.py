"""CS-19: rich uplink body."""

from __future__ import annotations

import json

from fastapi.testclient import TestClient

from app.config import get_settings
from app.db import get_session_factory
from app.main import app
from app.services.sync_pipeline import run_sync_for_kf
from app.services.uplink_hook import HermesUplinkHook
from tests.conftest import build_mock_wecom_client, load_json_fixture


def test_uplink_body_is_rich(loaded_seed, wecom_env, monkeypatch):
    monkeypatch.setenv("CSERVICE_SERVICE_TOKEN", "tok")
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
        body = msg["body"]
        assert "【客服账号】" in body
        assert "【近期对话】" in body
        assert "【本轮待回复】" in body
        assert "【起草要求】" in body
        assert body != "客户：你好，想咨询价格"
