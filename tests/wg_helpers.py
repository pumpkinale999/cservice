"""Shared helpers for WeCom group (wg) tests."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from app.models import WgDraft, WgGroup, WgMessage, WgReplyAnchor, WgSession

TOKEN = "test-service-token"
HEADERS = {
    "Authorization": f"Bearer {TOKEN}",
    "X-Skstudio-User-Id": "zhangsan",
}
INGRESS_URL = "/api/v1/cservice/_internal/wecom-group/ingress"


def _now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def seed_wg_group_session(
    db: Session,
    *,
    chatid: str = "wrGROUP001",
    ibot_id: str = "ibot_test_001",
    display_name: str = "测试健康群",
    pending_reply_count: int = 0,
) -> tuple[WgSession, WgGroup]:
    now = _now()
    group = WgGroup(
        chatid=chatid,
        ibot_id=ibot_id,
        display_name=display_name,
        status="active",
        created_at=now,
    )
    db.add(group)
    session = WgSession(
        id=str(uuid.uuid4()),
        chatid=chatid,
        status="open",
        pending_reply_count=pending_reply_count,
        last_activity_at=now,
    )
    db.add(session)
    db.flush()
    return session, group


def seed_wg_anchor(
    db: Session,
    *,
    chatid: str,
    response_url: str = "https://example.com/response",
) -> WgReplyAnchor:
    now = _now()
    expires = (datetime.now(UTC).replace(microsecond=0) + timedelta(hours=1)).isoformat()
    anchor = WgReplyAnchor(
        chatid=chatid,
        response_url=response_url,
        expires_at=expires,
        source_msgid="msg_anchor",
        updated_at=now,
    )
    db.add(anchor)
    db.flush()
    return anchor


def seed_wg_draft(
    db: Session,
    *,
    session_id: str,
    agent_text: str = "您好，建议如下。",
    version: int = 1,
) -> WgDraft:
    draft = WgDraft(
        id=str(uuid.uuid4()),
        session_id=session_id,
        agent_text=agent_text,
        status="pending",
        version=version,
        superseded_reason=None,
        created_at=_now(),
    )
    db.add(draft)
    db.flush()
    return draft


def seed_wg_inbound(
    db: Session,
    *,
    session_id: str,
    source_msgid: str,
    content: str,
    sender_userid: str = "user_alice",
) -> WgMessage:
    msg = WgMessage(
        id=str(uuid.uuid4()),
        session_id=session_id,
        direction="inbound",
        source_msgid=source_msgid,
        msg_type="text",
        content=content,
        sender_userid=sender_userid,
        sender_type="user",
        delivery_status="received",
        created_at=_now(),
    )
    db.add(msg)
    db.flush()
    return msg
