"""Webhook → sync → DB integration."""

from __future__ import annotations

from pathlib import Path

from app.db import get_session_factory
from app.models import Message
from app.services.kf_webhook_handler import handle_kf_event_plain
from app.services.sync_job import run_sync_job_now, set_sync_runner
from tests.conftest import build_mock_wecom_client, load_json_fixture

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "cservice"


def test_webhook_to_db_integration(loaded_seed, wecom_env):
    client_mock = build_mock_wecom_client(
        sync_responses=[load_json_fixture("sync_msg_text_inbound.json")]
    )
    sync_calls = []

    def run_sync(open_kfid: str, token: str | None) -> None:
        sync_calls.append((open_kfid, token))
        run_sync_job_now(open_kfid, token, client_mock)

    set_sync_runner(run_sync)

    plain = (FIXTURES / "webhook_kf_msg_or_event.xml").read_text(encoding="utf-8")
    factory = get_session_factory()
    db = factory()
    try:
        assert handle_kf_event_plain(db, plain) is True
        assert db.query(Message).filter_by(direction="inbound").count() == 1
        assert len(sync_calls) == 1
        assert sync_calls[0][0] == "wkTEST_MINIMAL"
    finally:
        db.close()
    client_mock.send_text_msg.assert_not_called()
