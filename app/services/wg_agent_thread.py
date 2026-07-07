"""Ensure cservice_wg_agent_thread (§6 · CS-32)."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.models import WgAgentThread, WgSession


def _now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def ensure_wg_agent_thread(
    db: Session,
    *,
    ibot_id: str,
    chatid: str,
    session: WgSession,
) -> WgAgentThread:
    existing = (
        db.query(WgAgentThread)
        .filter_by(ibot_id=ibot_id, chatid=chatid)
        .one_or_none()
    )
    if existing is not None:
        return existing
    row = WgAgentThread(
        ibot_id=ibot_id,
        chatid=chatid,
        hermes_profile="cservice-group-assistant",
        uplink_pending=False,
        uplink_started_at=None,
        created_at=_now(),
    )
    db.add(row)
    db.flush()
    return row


def mark_uplink_pending(db: Session, thread: WgAgentThread) -> None:
    thread.uplink_pending = True
    thread.uplink_started_at = _now()
    db.flush()


def clear_uplink_pending(
    db: Session,
    *,
    thread_id: int | None = None,
    session_id: str | None = None,
) -> None:
    if thread_id is not None:
        row = db.get(WgAgentThread, thread_id)
    elif session_id is not None:
        wg_session = db.get(WgSession, session_id)
        if wg_session is None:
            return
        row = (
            db.query(WgAgentThread)
            .filter_by(chatid=wg_session.chatid)
            .one_or_none()
        )
    else:
        return
    if row is None:
        return
    row.uplink_pending = False
    row.uplink_started_at = None
    db.flush()


def maybe_clear_uplink_timeout(db: Session, thread: WgAgentThread) -> None:
    if not thread.uplink_pending or not thread.uplink_started_at:
        return
    try:
        started = datetime.fromisoformat(thread.uplink_started_at.replace("Z", "+00:00"))
        if started.tzinfo is None:
            started = started.replace(tzinfo=UTC)
    except ValueError:
        return
    elapsed = (datetime.now(UTC) - started).total_seconds()
    if elapsed > 30:
        thread.uplink_pending = False
        db.flush()
