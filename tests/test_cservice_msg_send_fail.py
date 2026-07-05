"""msg_send_fail tests (CS-16)."""

from __future__ import annotations

import uuid

from fastapi.testclient import TestClient

from app.config import get_settings
from app.db import get_session_factory
from app.main import app
from app.models import AuditLog, Customer, Message, Session as CSession
from app.services.sync_pipeline import run_sync_for_kf
from app.services.uplink_hook import NoopUplinkHook
from tests.conftest import build_mock_wecom_client, load_json_fixture

TOKEN = "test-service-token"
ZHANGSAN = "zhangsan"


def _seed_sent_outbound(db) -> str:
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
            servicer_userid=ZHANGSAN,
            status="open",
            pending_reply_count=0,
            last_activity_at="2026-07-05T12:00:00+00:00",
        )
    )
    db.add(
        Message(
            id=str(uuid.uuid4()),
            session_id=sid,
            direction="outbound",
            wx_msgid="wx_outbound_001",
            msg_type="text",
            content="sent",
            sender_type="agent",
            delivery_status="sent",
            created_at="2026-07-05T12:00:00+00:00",
        )
    )
    db.flush()
    return sid


def test_msg_send_fail_rollback_badge(loaded_seed, wecom_env):
    factory = get_session_factory()
    db = factory()
    try:
        sid = _seed_sent_outbound(db)
        db.commit()
        client = build_mock_wecom_client(
            sync_responses=[load_json_fixture("sync_msg_send_fail.json")]
        )
        run_sync_for_kf(
            db,
            "wkTEST_MINIMAL",
            token=None,
            client=client,
            uplink_hook=NoopUplinkHook(),
        )
        db.commit()
        session = db.get(CSession, sid)
        assert session.pending_reply_count == 1
        msg = db.query(Message).filter_by(wx_msgid="wx_outbound_001").one()
        assert msg.delivery_status == "failed"
        assert msg.wx_fail_type == 4
        assert db.query(AuditLog).filter_by(action="delivery_failed").count() == 1
    finally:
        db.close()


def test_thread_shows_delivery_error_after_fail(loaded_seed, wecom_env, monkeypatch):
    monkeypatch.setenv("CSERVICE_SERVICE_TOKEN", TOKEN)
    get_settings.cache_clear()
    factory = get_session_factory()
    db = factory()
    try:
        sid = _seed_sent_outbound(db)
        db.commit()
        client = build_mock_wecom_client(
            sync_responses=[load_json_fixture("sync_msg_send_fail.json")]
        )
        run_sync_for_kf(
            db,
            "wkTEST_MINIMAL",
            token=None,
            client=client,
            uplink_hook=NoopUplinkHook(),
        )
        db.commit()
    finally:
        db.close()

    http = TestClient(app)
    r = http.get(
        f"/api/v1/cservice/customers/{sid}/thread",
        headers={
            "Authorization": f"Bearer {TOKEN}",
            "X-Skstudio-User-Id": ZHANGSAN,
        },
    )
    assert r.status_code == 200
    out = r.json()["messages"][0]
    assert out["delivery_status"] == "failed"
    assert "48 小时" in out["delivery_error"]
