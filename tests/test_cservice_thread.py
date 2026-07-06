"""GET /customers/{id}/thread tests (M4 PR-1)."""

from __future__ import annotations

import uuid

from fastapi.testclient import TestClient

from app.config import get_settings
from app.db import get_session_factory
from app.main import app
from app.models import Customer, Draft, Message, Session as CSession

TOKEN = "test-service-token"
ZHANGSAN = "zhangsan"


def _auth_headers() -> dict[str, str]:
    return {
        "Authorization": f"Bearer {TOKEN}",
        "X-Skstudio-User-Id": ZHANGSAN,
    }


def _seed_thread(db) -> str:
    cid = str(uuid.uuid4())
    db.add(
        Customer(
            id=cid,
            external_userid="wm1",
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
            wx_msgid="in1",
            msg_type="text",
            content="你好",
            sender_type="customer",
            created_at="2026-07-05T12:00:00+00:00",
        )
    )
    db.add(
        Message(
            id=str(uuid.uuid4()),
            session_id=sid,
            direction="outbound",
            wx_msgid="out1",
            msg_type="text",
            content="您好",
            sender_type="agent",
            delivery_status="sent",
            created_at="2026-07-05T12:01:00+00:00",
        )
    )
    db.add(
        Message(
            id=str(uuid.uuid4()),
            session_id=sid,
            direction="outbound",
            wx_msgid="out2",
            msg_type="text",
            content="失败消息",
            sender_type="user",
            delivery_status="failed",
            wx_fail_type=4,
            created_at="2026-07-05T12:02:00+00:00",
        )
    )
    db.add(
        Draft(
            id=str(uuid.uuid4()),
            session_id=sid,
            agent_text="Agent 建议",
            status="pending",
            version=1,
            created_at="2026-07-05T12:03:00+00:00",
        )
    )
    db.flush()
    return sid


def test_thread_messages_and_draft(loaded_seed, monkeypatch):
    monkeypatch.setenv("CSERVICE_SERVICE_TOKEN", TOKEN)
    get_settings.cache_clear()
    factory = get_session_factory()
    db = factory()
    try:
        sid = _seed_thread(db)
        db.commit()
    finally:
        db.close()

    client = TestClient(app)
    r = client.get(f"/api/v1/cservice/customers/{sid}/thread", headers=_auth_headers())
    assert r.status_code == 200
    body = r.json()
    assert body["session_id"] == sid
    assert len(body["messages"]) == 3
    assert body["messages"][0]["direction"] == "inbound"
    failed = body["messages"][2]
    assert failed["delivery_status"] == "failed"
    assert "48 小时" in failed["delivery_error"]
    assert body["pending_draft"]["agent_text"] == "Agent 建议"
    assert body["pending_draft"]["version"] == 1
    assert "uplink_pending" in body
    assert body["uplink_pending"] is False


def test_uplink_pending_after_enqueue(loaded_seed, wecom_env, monkeypatch):
    monkeypatch.setenv("CSERVICE_SERVICE_TOKEN", TOKEN)
    get_settings.cache_clear()
    from app.hermes.uplink_queue import enqueue_uplink
    from app.models import AgentThread
    from app.services.agent_thread import ensure_agent_thread

    factory = get_session_factory()
    db = factory()
    try:
        sid = _seed_thread(db)
        csession = db.get(CSession, sid)
        thread = ensure_agent_thread(db, csession, "wm1")
        db.commit()
        enqueue_uplink(
            db,
            session_id=sid,
            thread_id=thread.id,
            open_kfid="wkTEST_MINIMAL",
            external_userid="wm1",
            text="新问题",
            trigger_wx_msgid="wx_new",
            supersede=False,
        )
        db.commit()
        thread = db.get(AgentThread, thread.id)
        assert thread.uplink_pending is True
    finally:
        db.close()

    client = TestClient(app)
    r = client.get(f"/api/v1/cservice/customers/{sid}/thread", headers=_auth_headers())
    assert r.status_code == 200
    assert r.json()["uplink_pending"] is True
