"""M7 servicer admin internal API tests (CS-26–27)."""

from __future__ import annotations

from unittest.mock import patch

from fastapi.testclient import TestClient

from app.config import get_settings
from app.main import app

TOKEN = "test-service-token"
HEADERS = {"Authorization": f"Bearer {TOKEN}"}


def test_is_participant_true(loaded_seed, monkeypatch):
    monkeypatch.setenv("CSERVICE_SERVICE_TOKEN", TOKEN)
    get_settings.cache_clear()

    client = TestClient(app)
    r = client.get(
        "/api/v1/cservice/_internal/users/101/is-participant",
        headers=HEADERS,
    )
    assert r.status_code == 200
    assert r.json()["is_participant"] is True


def test_is_participant_false(loaded_seed, monkeypatch):
    monkeypatch.setenv("CSERVICE_SERVICE_TOKEN", TOKEN)
    get_settings.cache_clear()

    client = TestClient(app)
    r = client.get(
        "/api/v1/cservice/_internal/users/999/is-participant",
        headers=HEADERS,
    )
    assert r.status_code == 200
    assert r.json()["is_participant"] is False


def test_put_servicers_replaces_and_syncs(loaded_seed, monkeypatch):
    monkeypatch.setenv("CSERVICE_SERVICE_TOKEN", TOKEN)
    get_settings.cache_clear()

    mock_client = __import__("unittest.mock", fromlist=["MagicMock"]).MagicMock()
    mock_client.servicer_list.return_value = {"errcode": 0, "servicer_list": []}
    mock_client.servicer_add.return_value = {
        "errcode": 0,
        "result_list": [
            {"userid": "lisi", "errcode": 0, "errmsg": "ok"},
        ],
    }
    mock_client.servicer_del.return_value = {"errcode": 0, "result_list": []}
    mock_client.__enter__ = lambda self: self
    mock_client.__exit__ = lambda *args: None

    client = TestClient(app)
    with patch("app.routes_internal.WecomKfClient", return_value=mock_client):
        r = client.put(
            "/api/v1/cservice/_internal/kf/wkTEST_MINIMAL/servicers",
            headers=HEADERS,
            json={
                "servicers": [
                    {"user_id": "102", "sort_order": 0, "servicer_userid": "lisi"},
                ],
            },
        )
    assert r.status_code == 200
    body = r.json()
    assert body["saved"] is True
    assert len(body["result_list"]) >= 1

    r2 = client.get(
        "/api/v1/cservice/_internal/kf/wkTEST_MINIMAL/servicers",
        headers=HEADERS,
    )
    servicers = r2.json()["servicers"]
    assert len(servicers) == 1
    assert servicers[0]["user_id"] == "102"


def test_put_servicers_wx_partial_failure(loaded_seed, monkeypatch):
    monkeypatch.setenv("CSERVICE_SERVICE_TOKEN", TOKEN)
    get_settings.cache_clear()

    mock_client = __import__("unittest.mock", fromlist=["MagicMock"]).MagicMock()
    mock_client.servicer_list.return_value = {"errcode": 0, "servicer_list": []}
    mock_client.servicer_add.return_value = {
        "errcode": 0,
        "result_list": [
            {"userid": "wangwu", "errcode": 95014, "errmsg": "not in scope"},
        ],
    }
    mock_client.servicer_del.return_value = {"errcode": 0, "result_list": []}
    mock_client.__enter__ = lambda self: self
    mock_client.__exit__ = lambda *args: None

    client = TestClient(app)
    with patch("app.routes_internal.WecomKfClient", return_value=mock_client):
        r = client.put(
            "/api/v1/cservice/_internal/kf/wkTEST_MINIMAL/servicers",
            headers=HEADERS,
            json={
                "servicers": [
                    {"user_id": "103", "sort_order": 0, "servicer_userid": "wangwu"},
                ],
            },
        )
    assert r.status_code == 200
    results = r.json()["result_list"]
    assert any(item["errcode"] == 95014 for item in results)


def test_get_kf_accounts(loaded_seed, monkeypatch):
    monkeypatch.setenv("CSERVICE_SERVICE_TOKEN", TOKEN)
    get_settings.cache_clear()

    client = TestClient(app)
    r = client.get(
        "/api/v1/cservice/_internal/kf/accounts",
        headers=HEADERS,
    )
    assert r.status_code == 200
    accounts = r.json()["accounts"]
    assert len(accounts) == 1
    assert accounts[0]["open_kfid"] == "wkTEST_MINIMAL"
