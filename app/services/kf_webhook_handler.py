"""kf webhook event handling (§20)."""

from __future__ import annotations

import logging
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.models import WebhookDedup
from app.services.sync_job import enqueue_sync
from app.services.wecom_kf_crypto import parse_kf_event_xml

logger = logging.getLogger(__name__)


def _now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def try_record_webhook_dedup(db: Session, open_kfid: str, token: str) -> bool:
    """Return True if this is the first time seeing (open_kfid, token)."""
    key = f"kf:{open_kfid}:{token}"
    existing = db.get(WebhookDedup, key)
    if existing is not None:
        return False
    db.add(WebhookDedup(dedup_key=key, processed_at=_now()))
    db.commit()
    return True


def handle_kf_event_plain(db: Session, plain_xml: str) -> bool:
    """Parse event and enqueue sync if new. Returns True if enqueued."""
    fields = parse_kf_event_xml(plain_xml)
    if fields.get("Event") != "kf_msg_or_event":
        return False
    token = fields.get("Token", "").strip()
    open_kfid = fields.get("OpenKfId", "").strip()
    if not token or not open_kfid:
        logger.warning("kf event missing token/open_kfid")
        return False
    if not try_record_webhook_dedup(db, open_kfid, token):
        return False
    enqueue_sync(open_kfid, token)
    return True
