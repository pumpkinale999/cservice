"""Draft lifecycle (§15.4 · §22.4)."""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.models import Draft, Message

logger = logging.getLogger(__name__)


def _now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def supersede_pending_drafts(db: Session, session_id: str, reason: str) -> None:
    pending = (
        db.query(Draft)
        .filter_by(session_id=session_id, status="pending")
        .all()
    )
    for d in pending:
        d.status = "superseded"
        d.superseded_reason = reason


def latest_inbound_wx_msgid(db: Session, session_id: str) -> str | None:
    row = (
        db.query(Message)
        .filter_by(session_id=session_id, direction="inbound", msg_type="text")
        .order_by(Message.created_at.desc())
        .first()
    )
    if row is None or not row.wx_msgid:
        return None
    return str(row.wx_msgid)


def upsert_draft_pending(db: Session, session_id: str, agent_text: str) -> Draft:
    supersede_pending_drafts(db, session_id, "new_downlink")
    draft = Draft(
        id=str(uuid.uuid4()),
        session_id=session_id,
        agent_text=agent_text,
        status="pending",
        superseded_reason=None,
        created_at=_now(),
    )
    db.add(draft)
    db.flush()
    return draft


def upsert_draft_failed(db: Session, session_id: str, agent_text: str = "") -> Draft:
    supersede_pending_drafts(db, session_id, "agent_failed")
    text = agent_text or "Agent 暂不可用"
    draft = Draft(
        id=str(uuid.uuid4()),
        session_id=session_id,
        agent_text=text,
        status="failed",
        superseded_reason=None,
        created_at=_now(),
    )
    db.add(draft)
    db.flush()
    return draft


def should_accept_downlink(
    db: Session,
    session_id: str,
    trigger_wx_msgid: str | None,
) -> bool:
    """§22.4: discard downlink if trigger no longer matches latest inbound."""
    if not trigger_wx_msgid:
        return True
    latest = latest_inbound_wx_msgid(db, session_id)
    if latest is None:
        return False
    if latest != trigger_wx_msgid:
        logger.info(
            "discard stale downlink session=%s trigger=%s latest=%s",
            session_id,
            trigger_wx_msgid,
            latest,
        )
        return False
    return True
