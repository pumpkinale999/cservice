"""Downlink draft handler (§15.4)."""

from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from app.hermes.schemas import CserviceDraftReply
from app.services.draft_service import (
    should_accept_downlink,
    upsert_draft_failed,
    upsert_draft_pending,
)

logger = logging.getLogger(__name__)


def apply_draft_downlink(db: Session, frame: CserviceDraftReply) -> bool:
    """Persist draft from Gateway. Never calls send_msg."""
    if not should_accept_downlink(db, frame.session_id, frame.trigger_wx_msgid):
        return False
    if frame.stream_status == "failed":
        upsert_draft_failed(db, frame.session_id, frame.body)
    else:
        upsert_draft_pending(db, frame.session_id, frame.body)
    db.commit()
    return True
