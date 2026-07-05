"""send-edited tests (CS-07)."""

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


def test_send_draft_edited_two_messages(loaded_seed, monkeypatch):
    monkeypatch.setenv("CSERVICE_SERVICE_TOKEN", TOKEN)
    get_settings.cache_clear()
    factory = get_session_factory()
    db = factory()
    try:
        sid, draft_id = seed_session_with_draft(db, agent_text="Agent 原文")
        db.commit()
    finally:
        db.close()

    mock_client = MagicMock()
    mock_client.send_text_msg.return_value = load_json_fixture("send_msg_ok.json")

    with patch("app.routes_cservice._wecom_client", return_value=mock_client):
        client = TestClient(app)
        r = client.post(
            f"/api/v1/cservice/drafts/{draft_id}/send-edited",
            headers={
                "Authorization": f"Bearer {TOKEN}",
                "X-Skstudio-User-Id": ZHANGSAN,
            },
            json={"text": "用户定稿"},
        )

    assert r.status_code == 200
    mock_client.send_text_msg.assert_called_once_with(
        "wkTEST_MINIMAL", "wmTEST001", "用户定稿"
    )

    db2 = factory()
    try:
        outs = (
            db2.query(Message)
            .filter_by(session_id=sid, direction="outbound")
            .order_by(Message.created_at.asc())
            .all()
        )
        assert len(outs) == 2
        assert outs[0].sender_type == "agent"
        assert outs[0].content == "Agent 原文"
        assert outs[0].delivery_status == "draft_only"
        assert outs[1].sender_type == "user"
        assert outs[1].content == "用户定稿"
        assert outs[1].delivery_status == "sent"
        audit = db2.query(AuditLog).filter_by(action="send_edited").one()
        assert audit.edited_text == "用户定稿"
    finally:
        db2.close()
