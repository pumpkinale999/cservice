from fastapi.testclient import TestClient

from app.main import app


def test_health_m1(tmp_cservice_db):
    client = TestClient(app)
    r = client.get("/api/v1/cservice/health")
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is True
    assert body["db"] is True
    assert body["hermes_cservice_gateway"] is False
    assert body["open_kfid_count"] == 0
    assert body["service"] == "cservice"


def test_health_hermes_gateway_registered(tmp_cservice_db, monkeypatch):
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
        body = client.get("/api/v1/cservice/health").json()
        assert body["hermes_cservice_gateway"] is True


def test_health_wecom_token_ok(wecom_env, tmp_cservice_db, monkeypatch):
    monkeypatch.setattr(
        "app.routes_cservice.probe_wecom_token",
        lambda settings=None: "ok",
    )
    client = TestClient(app)
    body = client.get("/api/v1/cservice/health").json()
    assert body["wecom_token"] == "ok"
    assert body["ok"] is True


def test_health_wecom_token_error(wecom_env, tmp_cservice_db, monkeypatch):
    monkeypatch.setattr(
        "app.routes_cservice.probe_wecom_token",
        lambda settings=None: "error",
    )
    client = TestClient(app)
    body = client.get("/api/v1/cservice/health").json()
    assert body["wecom_token"] == "error"
    assert body["ok"] is False


def test_health_open_kfid_count_after_seed(tmp_cservice_db):
    from pathlib import Path

    from app.db import get_session_factory
    from app.services.seed import load_seed_file

    factory = get_session_factory()
    session = factory()
    fixture = Path(__file__).resolve().parent / "fixtures" / "cservice" / "seed_minimal.yaml"
    try:
        load_seed_file(fixture, session)
    finally:
        session.close()

    client = TestClient(app)
    body = client.get("/api/v1/cservice/health").json()
    assert body["open_kfid_count"] == 1


def test_health_wecom_group_ingress_disabled(tmp_cservice_db):
    client = TestClient(app)
    body = client.get("/api/v1/cservice/health").json()
    assert body["wecom_group_ingress"] is False
    assert body["wecom_group_assistant_gateway"] is False


def test_health_wecom_group_ingress_enabled(tmp_cservice_db, monkeypatch):
    from app.config import get_settings

    monkeypatch.setenv("CSERVICE_WG_ENABLED", "1")
    get_settings.cache_clear()
    client = TestClient(app)
    body = client.get("/api/v1/cservice/health").json()
    assert body["wecom_group_ingress"] is True
    assert body["wecom_group_assistant_gateway"] is False
    get_settings.cache_clear()
