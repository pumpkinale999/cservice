"""Assign retry on trans failure."""

from __future__ import annotations

from app.db import get_session_factory
from app.models import AssignRetry, Session as CSession
from app.services.sync_pipeline import run_sync_for_kf
from tests.conftest import build_mock_wecom_client, load_json_fixture


def test_assign_retry_on_trans_fail(loaded_seed, wecom_env):
    client = build_mock_wecom_client(
        sync_responses=[load_json_fixture("sync_msg_text_inbound.json")],
        trans_ok=False,
    )
    factory = get_session_factory()
    db = factory()
    try:
        run_sync_for_kf(db, "wkTEST_MINIMAL", token="T1", client=client)
        session = db.query(CSession).one()
        assert session.servicer_userid is None
        retry = db.query(AssignRetry).one()
        assert retry.attempts == 1
        assert retry.last_errcode == 95014
    finally:
        db.close()
