"""Downlink race discard (§22.4)."""

from __future__ import annotations

import uuid

from app.db import get_session_factory
from app.hermes.downlink_handler import apply_draft_downlink
from app.hermes.schemas import CserviceDraftReply
from app.models import Customer, Draft, Message, Session as CSession
from tests.conftest import load_json_fixture


def test_stale_trigger_discarded(loaded_seed):
    raw = load_json_fixture("draft_reply_downlink.json")
    factory = get_session_factory()
    db = factory()
    try:
        cid = str(uuid.uuid4())
        db.add(
            Customer(
                id=cid,
                external_userid="wmTEST001",
                display_name="c",
                created_at="2026-07-05T12:00:00+00:00",
            )
        )
        sid = str(uuid.uuid4())
        db.add(
            CSession(
                id=sid,
                open_kfid="wkTEST_MINIMAL",
                customer_id=cid,
                servicer_userid="zhangsan",
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
                wx_msgid="msg_newer",
                msg_type="text",
                content="new",
                sender_type="customer",
                created_at="2026-07-05T12:01:00+00:00",
            )
        )
        db.flush()
        raw["session_id"] = sid
        raw["trigger_wx_msgid"] = "msg_inbound_001"
        frame = CserviceDraftReply.from_dict(raw)
        assert frame is not None
        assert apply_draft_downlink(db, frame) is False
        assert db.query(Draft).filter_by(session_id=sid).count() == 0
    finally:
        db.close()
