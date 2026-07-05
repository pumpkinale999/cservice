"""send_msg outbound tests (CS-02 · CS-06)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from app.config import get_settings
from app.db import get_session_factory
from app.main import app
from app.models import AuditLog, Message, Session as CSession
from tests.conftest import load_json_fixture
from tests.cservice_send_helpers import ZHANGSAN, seed_session_with_draft

TOKEN = "test-service-token"


def _headers() -> dict[str, str]:
    return {
        "Authorization": f"Bearer {TOKEN}",
        "X-Skstudio-User-Id": ZHANGSAN,
    }


def test_send_draft_as_agent(loaded_seed, monkeypatch):
    monkeypatch.setenv("CSERVICE_SERVICE_TOKEN", TOKEN)
    get_settings.cache_clear()
    factory = get_session_factory()
    db = factory()
    try:
        sid, draft_id = seed_session_with_draft(db)
        db.commit()
    finally:
        db.close()

    send_ok = load_json_fixture("send_msg_ok.json")
    mock_client = MagicMock()
    mock_client.send_text_msg.return_value = send_ok

    with patch("app.routes_cservice._wecom_client", return_value=mock_client):
        client = TestClient(app)
        r = client.post(f"/api/v1/cservice/drafts/{draft_id}/send", headers=_headers())

    assert r.status_code == 200
    mock_client.send_text_msg.assert_called_once()
    assert r.json()["wx_msgid"] == "wx_outbound_001"

    db2 = factory()
    try:
        session = db2.get(CSession, sid)
        assert session.pending_reply_count == 0
        out = db2.query(Message).filter_by(session_id=sid, direction="outbound").one()
        assert out.sender_type == "agent"
        assert out.delivery_status == "sent"
        audit = db2.query(AuditLog).filter_by(action="send_agent").one()
        assert audit.draft_id == draft_id
    finally:
        db2.close()
