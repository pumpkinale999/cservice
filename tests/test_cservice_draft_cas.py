"""CS-24: draft expected_version CAS."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from app.config import get_settings
from app.db import get_session_factory
from app.main import app
from app.models import Draft
from tests.conftest import load_json_fixture
from tests.cservice_send_helpers import ZHANGSAN, seed_session_with_draft

TOKEN = "test-service-token"


def _headers() -> dict[str, str]:
    return {
        "Authorization": f"Bearer {TOKEN}",
        "X-Skstudio-User-Id": ZHANGSAN,
    }


def test_send_requires_expected_version(loaded_seed, monkeypatch):
    monkeypatch.setenv("CSERVICE_SERVICE_TOKEN", TOKEN)
    get_settings.cache_clear()
    factory = get_session_factory()
    db = factory()
    try:
        _sid, draft_id = seed_session_with_draft(db)
        db.commit()
    finally:
        db.close()

    client = TestClient(app)
    r = client.post(
        f"/api/v1/cservice/drafts/{draft_id}/send",
        headers=_headers(),
        json={},
    )
    assert r.status_code == 422


def test_concurrent_send_second_gets_409(loaded_seed, monkeypatch):
    monkeypatch.setenv("CSERVICE_SERVICE_TOKEN", TOKEN)
    get_settings.cache_clear()
    factory = get_session_factory()
    db = factory()
    try:
        _sid, draft_id = seed_session_with_draft(db)
        version = db.get(Draft, draft_id).version
        db.commit()
    finally:
        db.close()

    send_ok = load_json_fixture("send_msg_ok.json")
    mock_client = MagicMock()
    mock_client.send_text_msg.return_value = send_ok

    with patch("app.routes_cservice._wecom_client", return_value=mock_client):
        client = TestClient(app)
        body = {"expected_version": version}
        r1 = client.post(
            f"/api/v1/cservice/drafts/{draft_id}/send",
            headers=_headers(),
            json=body,
        )
        r2 = client.post(
            f"/api/v1/cservice/drafts/{draft_id}/send",
            headers=_headers(),
            json=body,
        )

    assert r1.status_code == 200
    assert r2.status_code == 409
    assert r2.json()["detail"]["code"] == "draft_concurrent_conflict"
    assert mock_client.send_text_msg.call_count == 1
