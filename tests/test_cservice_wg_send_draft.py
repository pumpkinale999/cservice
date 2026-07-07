"""WeCom group draft send tests (CS-30)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from app.config import get_settings
from app.db import get_session_factory
from app.main import app
from app.models import WgAuditLog, WgMessage
from tests.wg_helpers import HEADERS, TOKEN, seed_wg_anchor, seed_wg_draft, seed_wg_group_session


def test_send_wg_draft_as_agent(tmp_cservice_db, monkeypatch):
    monkeypatch.setenv("CSERVICE_SERVICE_TOKEN", TOKEN)
    monkeypatch.setenv("CSERVICE_WG_ENABLED", "1")
    monkeypatch.setenv("CSERVICE_DEMO_OUTBOUND", "1")
    get_settings.cache_clear()

    factory = get_session_factory()
    db = factory()
    try:
        session, group = seed_wg_group_session(db, pending_reply_count=1)
        seed_wg_anchor(db, chatid=group.chatid)
        draft = seed_wg_draft(db, session_id=session.id, version=1)
        db.commit()
        sid = session.id
        draft_id = draft.id
    finally:
        db.close()

    mock_client = MagicMock()
    with patch("app.routes_cservice._aibot_client", return_value=mock_client):
        client = TestClient(app)
        r = client.post(
            f"/api/v1/cservice/wg/drafts/{draft_id}/send",
            headers=HEADERS,
            json={"expected_version": 1},
        )

    assert r.status_code == 200
    assert r.json()["delivery_status"] == "sent"

    db2 = factory()
    try:
        from app.models import WgSession

        session = db2.get(WgSession, sid)
        assert session.pending_reply_count == 0
        out = db2.query(WgMessage).filter_by(session_id=sid, direction="outbound").one()
        assert out.sender_type == "agent"
        assert out.delivery_status == "sent"
        audit = db2.query(WgAuditLog).filter_by(action="wg_send_agent").one()
        assert audit.draft_id == draft_id
    finally:
        db2.close()
