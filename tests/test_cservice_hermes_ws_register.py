"""WSS gateway register tests (M3 · P4-M2 dual-role)."""

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


def test_ws_dual_gateway_register(tmp_cservice_db, monkeypatch):
    """kf and group gateways can register concurrently (P4-M2)."""
    monkeypatch.setenv("CSERVICE_SERVICE_TOKEN", "test-ws-token")
    from app.config import get_settings

    get_settings.cache_clear()
    client = TestClient(app)

    with client.websocket_connect(
        "/ws/hermes",
        headers={"Authorization": "Bearer test-ws-token"},
    ) as ws_kf:
        ws_kf.send_json(
            {
                "type": "gateway_register",
                "gateway_role": "cservice",
                "agent_slug": "cservice-assistant",
            }
        )
        assert json.loads(ws_kf.receive_text())["type"] == "gateway_register_ok"

        with client.websocket_connect(
            "/ws/hermes",
            headers={"Authorization": "Bearer test-ws-token"},
        ) as ws_group:
            ws_group.send_json(
                {
                    "type": "gateway_register",
                    "gateway_role": "cservice-group",
                    "agent_slug": "cservice-group-assistant",
                }
            )
            assert json.loads(ws_group.receive_text())["type"] == "gateway_register_ok"

            health = client.get("/api/v1/cservice/health").json()
            assert health["hermes_cservice_gateway"] is True
            assert health["wecom_group_assistant_gateway"] is True


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
