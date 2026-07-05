"""Shared seed helpers for M4 send tests."""

from __future__ import annotations

import uuid

from app.models import Customer, Draft, Message, Session as CSession

ZHANGSAN = "zhangsan"


def seed_session_with_draft(db, *, agent_text: str = "您好，请问需要什么帮助？") -> tuple[str, str]:
    cid = str(uuid.uuid4())
    db.add(
        Customer(
            id=cid,
            external_userid="wmTEST001",
            display_name="客户A",
            created_at="2026-07-05T12:00:00+00:00",
        )
    )
    sid = str(uuid.uuid4())
    db.add(
        CSession(
            id=sid,
            open_kfid="wkTEST_MINIMAL",
            customer_id=cid,
            servicer_userid=ZHANGSAN,
            status="open",
            pending_reply_count=1,
            last_activity_at="2026-07-05T12:00:00+00:00",
        )
    )
    db.add(
        Message(
            id=str(uuid.uuid4()),
            session_id=sid,
            direction="inbound",
            wx_msgid="inbound_001",
            msg_type="text",
            content="你好",
            sender_type="customer",
            created_at="2026-07-05T12:00:00+00:00",
        )
    )
    draft_id = str(uuid.uuid4())
    db.add(
        Draft(
            id=draft_id,
            session_id=sid,
            agent_text=agent_text,
            status="pending",
            created_at="2026-07-05T12:01:00+00:00",
        )
    )
    db.flush()
    return sid, draft_id
