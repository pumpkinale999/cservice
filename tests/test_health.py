from fastapi.testclient import TestClient

from app.main import app


def test_health_m1(tmp_cservice_db):
    client = TestClient(app)
    r = client.get("/api/v1/cservice/health")
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is True
    assert body["db"] is True
    assert body["hermes_cservice_gateway"] is None
    assert body["service"] == "cservice"
