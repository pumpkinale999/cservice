"""Send forbidden / validation tests."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from app.config import get_settings
from app.db import get_session_factory
from app.main import app
from app.models import Customer, Draft, Session as CSession
from tests.cservice_send_helpers import ZHANGSAN, seed_session_with_draft

TOKEN = "test-service-token"
LISI = "lisi"


def _headers(actor: str = ZHANGSAN) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {TOKEN}",
        "X-Skstudio-User-Id": actor,
    }


def test_send_pool_allows_any_servicer(loaded_seed, monkeypatch):
    monkeypatch.setenv("CSERVICE_SERVICE_TOKEN", TOKEN)
    get_settings.cache_clear()
    factory = get_session_factory()
    db = factory()
    try:
        _sid, draft_id = seed_session_with_draft(db)
        db.commit()
    finally:
        db.close()

    mock_client = MagicMock()
    mock_client.send_text_msg.return_value = {"errcode": 0, "msgid": "wx_out_1"}
    with patch("app.routes_cservice._wecom_client", return_value=mock_client):
        client = TestClient(app)
        r = client.post(
            f"/api/v1/cservice/drafts/{draft_id}/send",
            headers=_headers(LISI),
        )
    assert r.status_code == 200
    mock_client.send_text_msg.assert_called_once()


def test_send_draft_superseded(loaded_seed, monkeypatch):
    monkeypatch.setenv("CSERVICE_SERVICE_TOKEN", TOKEN)
    get_settings.cache_clear()
    factory = get_session_factory()
    db = factory()
    try:
        _sid, draft_id = seed_session_with_draft(db)
        draft = db.get(Draft, draft_id)
        draft.status = "superseded"
        db.commit()
    finally:
        db.close()

    mock_client = MagicMock()
    with patch("app.routes_cservice._wecom_client", return_value=mock_client):
        client = TestClient(app)
        r = client.post(
            f"/api/v1/cservice/drafts/{draft_id}/send",
            headers=_headers(),
        )
    assert r.status_code == 409


def test_send_closed_session(loaded_seed, monkeypatch):
    monkeypatch.setenv("CSERVICE_SERVICE_TOKEN", TOKEN)
    get_settings.cache_clear()
    factory = get_session_factory()
    db = factory()
    try:
        sid, draft_id = seed_session_with_draft(db)
        session = db.get(CSession, sid)
        session.status = "closed"
        db.commit()
    finally:
        db.close()

    mock_client = MagicMock()
    with patch("app.routes_cservice._wecom_client", return_value=mock_client):
        client = TestClient(app)
        r = client.post(
            f"/api/v1/cservice/drafts/{draft_id}/send",
            headers=_headers(),
        )
    assert r.status_code == 409


def test_send_empty_text(loaded_seed, monkeypatch):
    monkeypatch.setenv("CSERVICE_SERVICE_TOKEN", TOKEN)
    get_settings.cache_clear()
    factory = get_session_factory()
    db = factory()
    try:
        sid, _draft_id = seed_session_with_draft(db)
        db.commit()
    finally:
        db.close()

    mock_client = MagicMock()
    with patch("app.routes_cservice._wecom_client", return_value=mock_client):
        client = TestClient(app)
        r = client.post(
            f"/api/v1/cservice/customers/{sid}/send-manual",
            headers=_headers(),
            json={"text": "   "},
        )
    assert r.status_code == 422


def test_send_wecom_error_502(loaded_seed, monkeypatch):
    monkeypatch.setenv("CSERVICE_SERVICE_TOKEN", TOKEN)
    get_settings.cache_clear()
    factory = get_session_factory()
    db = factory()
    try:
        _sid, draft_id = seed_session_with_draft(db)
        db.commit()
    finally:
        db.close()

    from app.services.wecom_errors import CserviceWecomError

    mock_client = MagicMock()
    mock_client.send_text_msg.side_effect = CserviceWecomError(95014, "fail")

    with patch("app.routes_cservice._wecom_client", return_value=mock_client):
        client = TestClient(app)
        r = client.post(
            f"/api/v1/cservice/drafts/{draft_id}/send",
            headers=_headers(),
        )
    assert r.status_code == 502
