"""Sync pipeline ingest (CS-01)."""

from __future__ import annotations

from app.db import get_session_factory
from app.models import Customer, Message
from app.services.sync_pipeline import run_sync_for_kf
from tests.conftest import build_mock_wecom_client, load_json_fixture


def test_sync_pipeline_inbound(loaded_seed, wecom_env):
    client = build_mock_wecom_client(
        sync_responses=[load_json_fixture("sync_msg_text_inbound.json")]
    )
    factory = get_session_factory()
    db = factory()
    try:
        run_sync_for_kf(db, "wkTEST_MINIMAL", token="T1", client=client)
        msgs = db.query(Message).filter_by(direction="inbound").all()
        assert len(msgs) == 1
        assert msgs[0].content == "你好，想咨询价格"
        assert db.query(Customer).filter_by(external_userid="wmTEST001").count() == 1
    finally:
        db.close()
    client.send_text_msg.assert_not_called()
