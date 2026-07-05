"""Handle async msg_send_fail events from sync_msg (§23.2)."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from app.models import AuditLog, Message, Session as CSession
from app.services.badge import on_send_fail_rollback

logger = logging.getLogger(__name__)


def _now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def apply_msg_send_fail(db: Session, event: dict[str, Any]) -> bool:
    """Mark outbound failed and rollback badge if needed. Returns True if updated."""
    fail_msgid = str(event.get("fail_msgid") or event.get("msgid") or "")
    if not fail_msgid:
        logger.warning("msg_send_fail missing fail_msgid: %s", event)
        return False

    msg = db.query(Message).filter_by(wx_msgid=fail_msgid).one_or_none()
    if msg is None:
        logger.info("msg_send_fail unknown wx_msgid=%s", fail_msgid)
        return False
    if msg.delivery_status == "failed":
        return False

    was_sent = msg.delivery_status == "sent"
    fail_type = event.get("fail_type")
    msg.delivery_status = "failed"
    if fail_type is not None:
        try:
            msg.wx_fail_type = int(fail_type)
        except (TypeError, ValueError):
            pass

    csession = db.get(CSession, msg.session_id)
    if csession is not None and was_sent:
        on_send_fail_rollback(csession)

    db.add(
        AuditLog(
            actor_user_id=None,
            action="delivery_failed",
            draft_id=msg.draft_id,
            edited_text=None,
            created_at=_now(),
        )
    )
    db.flush()
    return True
