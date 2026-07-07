"""WeCom group draft lifecycle (§15.4 · §22.4)."""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models import WgDraft, WgMessage

logger = logging.getLogger(__name__)


def _now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def _next_draft_version(db: Session, session_id: str) -> int:
    current = (
        db.query(func.max(WgDraft.version))
        .filter_by(session_id=session_id)
        .scalar()
    )
    return int(current or 0) + 1


def supersede_pending_wg_drafts(db: Session, session_id: str, reason: str) -> None:
    pending = (
        db.query(WgDraft)
        .filter_by(session_id=session_id, status="pending")
        .all()
    )
    for d in pending:
        d.status = "superseded"
        d.superseded_reason = reason


def latest_inbound_source_msgid(db: Session, session_id: str) -> str | None:
    row = (
        db.query(WgMessage)
        .filter_by(session_id=session_id, direction="inbound", msg_type="text")
        .order_by(WgMessage.created_at.desc())
        .first()
    )
    if row is None or not row.source_msgid:
        return None
    return str(row.source_msgid)


def upsert_wg_draft_pending(db: Session, session_id: str, agent_text: str) -> WgDraft:
    supersede_pending_wg_drafts(db, session_id, "new_downlink")
    draft = WgDraft(
        id=str(uuid.uuid4()),
        session_id=session_id,
        agent_text=agent_text,
        status="pending",
        version=_next_draft_version(db, session_id),
        superseded_reason=None,
        created_at=_now(),
    )
    db.add(draft)
    db.flush()
    return draft


def upsert_wg_draft_failed(db: Session, session_id: str, agent_text: str = "") -> WgDraft:
    supersede_pending_wg_drafts(db, session_id, "agent_failed")
    text = agent_text or "Agent 暂不可用"
    draft = WgDraft(
        id=str(uuid.uuid4()),
        session_id=session_id,
        agent_text=text,
        status="failed",
        version=_next_draft_version(db, session_id),
        superseded_reason=None,
        created_at=_now(),
    )
    db.add(draft)
    db.flush()
    return draft


def should_accept_wg_downlink(
    db: Session,
    session_id: str,
    trigger_source_msgid: str | None,
) -> bool:
    if not trigger_source_msgid:
        return True
    latest = latest_inbound_source_msgid(db, session_id)
    if latest is None:
        return False
    if latest != trigger_source_msgid:
        logger.info(
            "discard stale wg downlink session=%s trigger=%s latest=%s",
            session_id,
            trigger_source_msgid,
            latest,
        )
        return False
    return True
