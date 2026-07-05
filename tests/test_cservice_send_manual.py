"""send-manual tests (CS-13)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from app.config import get_settings
from app.db import get_session_factory
from app.main import app
from app.models import AuditLog, Message
from tests.conftest import load_json_fixture
from tests.cservice_send_helpers import ZHANGSAN, seed_session_with_draft

TOKEN = "test-service-token"


def test_send_manual_no_draft(loaded_seed, monkeypatch):
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
    mock_client.send_text_msg.return_value = load_json_fixture("send_msg_ok.json")

    with patch("app.routes_cservice._wecom_client", return_value=mock_client):
        client = TestClient(app)
        r = client.post(
            f"/api/v1/cservice/customers/{sid}/send-manual",
            headers={
                "Authorization": f"Bearer {TOKEN}",
                "X-Skstudio-User-Id": ZHANGSAN,
            },
            json={"text": "人工回复"},
        )

    assert r.status_code == 200
    db2 = factory()
    try:
        out = db2.query(Message).filter_by(session_id=sid, sender_type="user").one()
        assert out.draft_id is None
        assert out.content == "人工回复"
        audit = db2.query(AuditLog).filter_by(action="send_manual").one()
        assert audit.draft_id is None
    finally:
        db2.close()
