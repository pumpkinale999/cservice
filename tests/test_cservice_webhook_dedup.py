"""Webhook token dedup (CS-15)."""

from __future__ import annotations

import hashlib
from pathlib import Path

from app.db import get_session_factory
from app.models import WebhookDedup
from app.services.kf_webhook_handler import handle_kf_event_plain
from app.services.sync_job import set_sync_runner

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "cservice"


def test_webhook_token_dedup(loaded_seed, wecom_env):
    plain = (FIXTURES / "webhook_kf_msg_or_event.xml").read_text(encoding="utf-8")
    enqueued = []

    set_sync_runner(lambda kf, tok: enqueued.append((kf, tok)))

    factory = get_session_factory()
    db = factory()
    try:
        assert handle_kf_event_plain(db, plain) is True
        assert handle_kf_event_plain(db, plain) is False
        assert db.query(WebhookDedup).count() == 1
        assert len(enqueued) == 1
        assert enqueued[0] == ("wkTEST_MINIMAL", "CALLBACK_TOKEN_abc123")
    finally:
        db.close()
