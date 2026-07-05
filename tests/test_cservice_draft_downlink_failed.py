"""Draft failed downlink."""

from __future__ import annotations

import uuid

from app.db import get_session_factory
from app.hermes.downlink_handler import apply_draft_downlink
from app.hermes.schemas import CserviceDraftReply
from app.models import Customer, Draft, Session as CSession
from tests.conftest import load_json_fixture


def test_draft_failed(loaded_seed):
    raw = load_json_fixture("draft_reply_failed_downlink.json")
    factory = get_session_factory()
    db = factory()
    try:
        cid = str(uuid.uuid4())
        db.add(
            Customer(
                id=cid,
                external_userid="wmX",
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
                pending_reply_count=0,
                last_activity_at="2026-07-05T12:00:00+00:00",
            )
        )
        db.flush()
        raw["session_id"] = sid
        frame = CserviceDraftReply.from_dict(raw)
        assert frame is not None
        apply_draft_downlink(db, frame)
        row = db.query(Draft).filter_by(session_id=sid, status="failed").one()
        assert row.agent_text
    finally:
        db.close()
