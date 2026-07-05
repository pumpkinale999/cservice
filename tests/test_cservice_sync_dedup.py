"""wx_msgid dedup (CS-15)."""

from __future__ import annotations

from app.db import get_session_factory
from app.models import Message
from app.services.sync_pipeline import run_sync_for_kf
from tests.conftest import build_mock_wecom_client, load_json_fixture


def test_wx_msgid_dedup_on_resync(loaded_seed, wecom_env):
    payload = load_json_fixture("sync_msg_text_inbound.json")
    client = build_mock_wecom_client(sync_responses=[payload, payload])
    factory = get_session_factory()
    db = factory()
    try:
        run_sync_for_kf(db, "wkTEST_MINIMAL", token="T1", client=client)
        run_sync_for_kf(db, "wkTEST_MINIMAL", token=None, client=client)
        assert db.query(Message).count() == 1
    finally:
        db.close()
