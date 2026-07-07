"""WeCom group outbound skeleton tests."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock

from app.config import get_settings
from app.db import get_session_factory
from app.models import WgGroup, WgReplyAnchor, WgSession
from app.services.wecom_aibot_client import WecomAibotClient
from app.services.wg_outbound_service import send_text_to_group


def _seed_group_session_anchor(db, *, chatid: str = "wrOUT001") -> WgSession:
    now = datetime.now(UTC).replace(microsecond=0).isoformat()
    expires = (datetime.now(UTC).replace(microsecond=0) + timedelta(hours=1)).isoformat()
    db.add(
        WgGroup(
            chatid=chatid,
            ibot_id="ibot_test",
            display_name="出站测试群",
            status="active",
            created_at=now,
        )
    )
    session = WgSession(
        id="sess-out-001",
        chatid=chatid,
        status="open",
        pending_reply_count=1,
        last_activity_at=now,
    )
    db.add(session)
    db.add(
        WgReplyAnchor(
            chatid=chatid,
            response_url="https://example.com/response",
            expires_at=expires,
            source_msgid="msg_in_001",
            updated_at=now,
        )
    )
    db.flush()
    return session


def test_send_text_demo_clears_badge(tmp_cservice_db, monkeypatch):
    monkeypatch.setenv("CSERVICE_DEMO_OUTBOUND", "1")
    get_settings.cache_clear()

    factory = get_session_factory()
    db = factory()
    try:
        session = _seed_group_session_anchor(db)
        db.commit()

        mock_client = MagicMock(spec=WecomAibotClient)
        mock_client.post_response.return_value = {"errcode": 0}

        result = send_text_to_group(
            db,
            chatid="wrOUT001",
            text="  您好，请查收建议  ",
            client=mock_client,
            actor_user_id="user_101",
        )
        db.commit()

        assert result["ok"] is True
        assert result["pending_reply_count"] == 0
        db.refresh(session)
        assert session.pending_reply_count == 0
        mock_client.post_response.assert_called_once_with(
            "https://example.com/response",
            "您好，请查收建议",
        )
    finally:
        db.close()
        get_settings.cache_clear()
