"""Non-text inbound must not uplink (CS-12)."""

from __future__ import annotations

from app.db import get_session_factory
from app.models import Draft, UplinkRetry
from app.services.sync_pipeline import run_sync_for_kf
from app.services.uplink_hook import HermesUplinkHook
from tests.conftest import build_mock_wecom_client, load_json_fixture


def test_image_inbound_no_uplink(loaded_seed, wecom_env):
    client = build_mock_wecom_client(
        sync_responses=[load_json_fixture("sync_msg_image_inbound.json")]
    )
    factory = get_session_factory()
    db = factory()
    try:
        run_sync_for_kf(
            db,
            "wkTEST_MINIMAL",
            token="T1",
            client=client,
            uplink_hook=HermesUplinkHook(),
        )
        assert db.query(UplinkRetry).count() == 0
        assert db.query(Draft).count() == 0
    finally:
        db.close()
    client.send_text_msg.assert_not_called()
