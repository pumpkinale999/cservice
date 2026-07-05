"""origin=5 outbound ingest (D-CS-16)."""

from __future__ import annotations

from app.db import get_session_factory
from app.models import AuditLog, Message
from app.services.sync_pipeline import run_sync_for_kf
from tests.conftest import build_mock_wecom_client, load_json_fixture


def test_origin5_outbound_and_audit(loaded_seed, wecom_env):
    client = build_mock_wecom_client(
        sync_responses=[load_json_fixture("sync_msg_origin5_outbound.json")]
    )
    factory = get_session_factory()
    db = factory()
    try:
        run_sync_for_kf(db, "wkTEST_MINIMAL", token="T1", client=client)
        out = db.query(Message).filter_by(direction="outbound").one()
        assert out.sender_type == "user"
        assert "企微客户端" in (out.content or "")
        assert db.query(AuditLog).filter_by(action="send_wecom_client").count() == 1
    finally:
        db.close()
