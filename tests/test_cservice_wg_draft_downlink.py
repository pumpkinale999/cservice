"""WeCom group draft downlink tests (P4-M2)."""

from __future__ import annotations

import json

from fastapi.testclient import TestClient

from app.config import get_settings
from app.db import get_session_factory
from app.hermes.downlink_handler import apply_draft_downlink
from app.hermes.schemas import CserviceDraftReply
from app.main import app
from app.models import WgDraft
from tests.wg_helpers import seed_wg_group_session, seed_wg_inbound


def test_wg_draft_downlink_pending(tmp_cservice_db):
    factory = get_session_factory()
    db = factory()
    try:
        session, _group = seed_wg_group_session(db)
        seed_wg_inbound(
            db,
            session_id=session.id,
            source_msgid="m1",
            content="hello",
        )
        db.commit()

        ok = apply_draft_downlink(
            db,
            CserviceDraftReply(
                thread_id=1,
                session_id=session.id,
                body="您好，建议如下。",
                stream_status="final",
                trigger_source_msgid="m1",
            ),
        )
        assert ok is True
        draft = db.query(WgDraft).filter_by(session_id=session.id, status="pending").one()
        assert draft.agent_text == "您好，建议如下。"
    finally:
        db.close()


def test_wg_draft_downlink_via_ws(tmp_cservice_db, monkeypatch):
    monkeypatch.setenv("CSERVICE_SERVICE_TOKEN", "tok")
    get_settings.cache_clear()
    factory = get_session_factory()
    db = factory()
    try:
        session, _group = seed_wg_group_session(db)
        seed_wg_inbound(
            db,
            session_id=session.id,
            source_msgid="m1",
            content="hello",
        )
        db.commit()
        session_id = session.id
    finally:
        db.close()

    client = TestClient(app)
    with client.websocket_connect(
        "/ws/hermes",
        headers={"Authorization": "Bearer tok"},
    ) as ws:
        ws.send_json(
            {
                "type": "cservice_draft_reply",
                "thread_id": 1,
                "session_id": session_id,
                "body": "draft from agent",
                "stream_status": "final",
                "trigger_source_msgid": "m1",
            }
        )
        ack = json.loads(ws.receive_text())
        assert ack["type"] == "cservice_draft_reply_ok"
        assert ack["accepted"] is True

    db = factory()
    try:
        draft = db.query(WgDraft).filter_by(session_id=session.id, status="pending").one()
        assert draft.agent_text == "draft from agent"
    finally:
        db.close()
