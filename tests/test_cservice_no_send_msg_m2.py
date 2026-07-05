"""M2 hard gate: no send_msg."""

from __future__ import annotations

from app.db import get_session_factory
from app.services.sync_pipeline import run_sync_for_kf
from tests.conftest import build_mock_wecom_client, load_json_fixture


def test_no_send_msg_during_sync(loaded_seed, wecom_env):
    client = build_mock_wecom_client(
        sync_responses=[load_json_fixture("sync_msg_text_inbound.json")]
    )
    factory = get_session_factory()
    db = factory()
    try:
        run_sync_for_kf(db, "wkTEST_MINIMAL", token="T1", client=client)
    finally:
        db.close()
    client.send_text_msg.assert_not_called()
