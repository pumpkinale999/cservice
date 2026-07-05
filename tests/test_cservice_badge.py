"""Badge rules (D-CS-15)."""

from __future__ import annotations

from app.db import get_session_factory
from app.models import Session as CSession
from app.services.sync_pipeline import run_sync_for_kf
from tests.conftest import build_mock_wecom_client, load_json_fixture


def test_double_text_same_round_badge_one(loaded_seed, wecom_env):
    client = build_mock_wecom_client(
        sync_responses=[load_json_fixture("sync_msg_text_double_inbound.json")]
    )
    factory = get_session_factory()
    db = factory()
    try:
        run_sync_for_kf(db, "wkTEST_MINIMAL", token="T1", client=client)
        session = db.query(CSession).filter_by(open_kfid="wkTEST_MINIMAL").one()
        assert session.pending_reply_count == 1
    finally:
        db.close()


def test_origin5_clears_badge(loaded_seed, wecom_env):
    client = build_mock_wecom_client(
        sync_responses=[load_json_fixture("sync_msg_inbound_then_origin5.json")]
    )
    factory = get_session_factory()
    db = factory()
    try:
        run_sync_for_kf(db, "wkTEST_MINIMAL", token="T1", client=client)
        session = db.query(CSession).filter_by(open_kfid="wkTEST_MINIMAL").one()
        assert session.pending_reply_count == 0
    finally:
        db.close()
