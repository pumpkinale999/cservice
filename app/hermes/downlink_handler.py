"""Downlink draft handler (§15.4)."""

from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from app.hermes.schemas import CserviceDraftReply
from app.models import WgSession
from app.services.agent_thread import clear_uplink_pending
from app.services.draft_service import (
    should_accept_downlink,
    upsert_draft_failed,
    upsert_draft_pending,
)
from app.services.wg_agent_thread import clear_uplink_pending as clear_wg_uplink_pending
from app.services.wg_draft_service import (
    should_accept_wg_downlink,
    upsert_wg_draft_failed,
    upsert_wg_draft_pending,
)

logger = logging.getLogger(__name__)


def _is_wg_session(db: Session, session_id: str) -> bool:
    return db.get(WgSession, session_id) is not None


def apply_draft_downlink(db: Session, frame: CserviceDraftReply) -> bool:
    """Persist draft from Gateway. Never calls outbound send."""
    if _is_wg_session(db, frame.session_id):
        trigger = frame.trigger_source_msgid or frame.trigger_wx_msgid
        if not should_accept_wg_downlink(db, frame.session_id, trigger):
            return False
        if frame.stream_status == "failed":
            upsert_wg_draft_failed(db, frame.session_id, frame.body)
        else:
            upsert_wg_draft_pending(db, frame.session_id, frame.body)
        clear_wg_uplink_pending(db, session_id=frame.session_id)
        db.commit()
        return True

    if not should_accept_downlink(db, frame.session_id, frame.trigger_wx_msgid):
        return False
    if frame.stream_status == "failed":
        upsert_draft_failed(db, frame.session_id, frame.body)
    else:
        upsert_draft_pending(db, frame.session_id, frame.body)
    clear_uplink_pending(db, session_id=frame.session_id)
    db.commit()
    return True
