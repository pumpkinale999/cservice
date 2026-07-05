"""Draft service tests (M3 · PR-1)."""

from __future__ import annotations

import uuid

from app.db import get_session_factory
from app.models import Customer, Draft, Message, Session as CSession
from app.services.draft_service import (
    latest_inbound_wx_msgid,
    supersede_pending_drafts,
    upsert_draft_failed,
    upsert_draft_pending,
)


def _seed_session(db) -> CSession:
    cid = str(uuid.uuid4())
    customer = Customer(
        id=cid,
        external_userid=f"wm_{cid[:8]}",
        display_name="test",
        created_at="2026-07-05T12:00:00+00:00",
    )
    db.add(customer)
    sid = str(uuid.uuid4())
    row = CSession(
        id=sid,
        open_kfid="wkTEST_MINIMAL",
        customer_id=cid,
        servicer_userid="zhangsan",
        status="open",
        pending_reply_count=1,
        last_activity_at="2026-07-05T12:00:00+00:00",
    )
    db.add(row)
    db.flush()
    return row


def test_supersede_pending(loaded_seed):
    factory = get_session_factory()
    db = factory()
    try:
        csession = _seed_session(db)
        db.add(
            Draft(
                id=str(uuid.uuid4()),
                session_id=csession.id,
                agent_text="old",
                status="pending",
                created_at="2026-07-05T12:00:00+00:00",
            )
        )
        db.commit()
        supersede_pending_drafts(db, csession.id, "new_inbound")
        db.commit()
        pending = db.query(Draft).filter_by(session_id=csession.id, status="pending").count()
        superseded = db.query(Draft).filter_by(session_id=csession.id, status="superseded").count()
        assert pending == 0
        assert superseded == 1
    finally:
        db.close()


def test_upsert_draft_pending_unique(loaded_seed):
    factory = get_session_factory()
    db = factory()
    try:
        csession = _seed_session(db)
        upsert_draft_pending(db, csession.id, "draft one")
        upsert_draft_pending(db, csession.id, "draft two")
        db.commit()
        pending = db.query(Draft).filter_by(session_id=csession.id, status="pending").all()
        assert len(pending) == 1
        assert pending[0].agent_text == "draft two"
    finally:
        db.close()


def test_upsert_draft_failed(loaded_seed):
    factory = get_session_factory()
    db = factory()
    try:
        csession = _seed_session(db)
        upsert_draft_failed(db, csession.id)
        db.commit()
        row = db.query(Draft).filter_by(session_id=csession.id, status="failed").one()
        assert "不可用" in row.agent_text
    finally:
        db.close()


def test_latest_inbound_wx_msgid(loaded_seed):
    factory = get_session_factory()
    db = factory()
    try:
        csession = _seed_session(db)
        db.add(
            Message(
                id=str(uuid.uuid4()),
                session_id=csession.id,
                direction="inbound",
                wx_msgid="msg_a",
                msg_type="text",
                content="a",
                sender_type="customer",
                created_at="2026-07-05T12:00:00+00:00",
            )
        )
        db.add(
            Message(
                id=str(uuid.uuid4()),
                session_id=csession.id,
                direction="inbound",
                wx_msgid="msg_b",
                msg_type="text",
                content="b",
                sender_type="customer",
                created_at="2026-07-05T12:01:00+00:00",
            )
        )
        db.commit()
        assert latest_inbound_wx_msgid(db, csession.id) == "msg_b"
    finally:
        db.close()
