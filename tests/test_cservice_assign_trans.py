"""Assign trans (CS-03 · CS-14)."""

from __future__ import annotations

from app.db import get_session_factory
from app.models import Session as CSession
from app.services.sync_pipeline import run_sync_for_kf
from tests.conftest import build_mock_wecom_client, load_json_fixture


def test_assign_after_inbound(loaded_seed, wecom_env):
    client = build_mock_wecom_client(
        sync_responses=[load_json_fixture("sync_msg_text_inbound.json")]
    )
    factory = get_session_factory()
    db = factory()
    try:
        run_sync_for_kf(db, "wkTEST_MINIMAL", token="T1", client=client)
        session = db.query(CSession).one()
        assert session.servicer_userid == "lisi"
        assert session.status == "open"
        client.service_state_trans.assert_called_once()
        client.service_state_get.assert_called_once()
    finally:
        db.close()
