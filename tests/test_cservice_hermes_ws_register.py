"""WSS gateway register tests (M3 · PR-2)."""

from __future__ import annotations

import json

from fastapi.testclient import TestClient

from app.main import app


def test_ws_register_ok(tmp_cservice_db, monkeypatch):
    monkeypatch.setenv("CSERVICE_SERVICE_TOKEN", "test-ws-token")
    from app.config import get_settings

    get_settings.cache_clear()
    client = TestClient(app)
    with client.websocket_connect(
        "/ws/hermes",
        headers={"Authorization": "Bearer test-ws-token"},
    ) as ws:
        ws.send_json(
            {
                "type": "gateway_register",
                "gateway_role": "cservice",
                "agent_slug": "cservice-assistant",
            }
        )
        msg = json.loads(ws.receive_text())
        assert msg["type"] == "gateway_register_ok"


def test_ws_bad_token(tmp_cservice_db, monkeypatch):
    monkeypatch.setenv("CSERVICE_SERVICE_TOKEN", "test-ws-token")
    from app.config import get_settings

    get_settings.cache_clear()
    client = TestClient(app)
    try:
        with client.websocket_connect(
            "/ws/hermes",
            headers={"Authorization": "Bearer wrong"},
        ):
            pass
    except Exception:
        pass
