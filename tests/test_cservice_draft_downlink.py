"""Draft downlink tests (CS-04)."""

from __future__ import annotations

import json
import uuid

from app.db import get_session_factory
from app.hermes.downlink_handler import apply_draft_downlink
from app.hermes.schemas import CserviceDraftReply
from app.models import Customer, Draft, Message, Session as CSession
from tests.conftest import load_json_fixture


def _seed_with_inbound(db):
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
            wx_msgid="msg_inbound_001",
            msg_type="text",
            content="hi",
            sender_type="customer",
            created_at="2026-07-05T12:00:00+00:00",
        )
    )
    db.flush()
    return sid


def test_draft_downlink_pending(loaded_seed):
    raw = load_json_fixture("draft_reply_downlink.json")
    factory = get_session_factory()
    db = factory()
    try:
        sid = _seed_with_inbound(db)
        raw["session_id"] = sid
        frame = CserviceDraftReply.from_dict(raw)
        assert frame is not None
        assert apply_draft_downlink(db, frame) is True
        draft = db.query(Draft).filter_by(session_id=sid, status="pending").one()
        assert "您好" in draft.agent_text
    finally:
        db.close()


def test_draft_downlink_via_ws(loaded_seed, monkeypatch):
    monkeypatch.setenv("CSERVICE_SERVICE_TOKEN", "tok")
    from app.config import get_settings
    from fastapi.testclient import TestClient

    from app.main import app

    get_settings.cache_clear()
    factory = get_session_factory()
    db = factory()
    sid = _seed_with_inbound(db)
    db.commit()
    db.close()

    raw = load_json_fixture("draft_reply_downlink.json")
    raw["session_id"] = sid
    client = TestClient(app)
    with client.websocket_connect(
        "/ws/hermes",
        headers={"Authorization": "Bearer tok"},
    ) as ws:
        ws.send_json(
            {
                "type": "gateway_register",
                "gateway_role": "cservice",
                "agent_slug": "cservice-assistant",
            }
        )
        ws.receive_text()
        ws.send_json(raw)
        ack = json.loads(ws.receive_text())
        assert ack["accepted"] is True
    db2 = factory()
    try:
        assert db2.query(Draft).filter_by(session_id=sid, status="pending").count() == 1
    finally:
        db2.close()
