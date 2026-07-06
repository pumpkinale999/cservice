"""Ensure cservice_agent_thread after assign (§21.2 step 5 · §13.5 · CS-20)."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.models import AgentThread, Session as CSession


def _now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def ensure_agent_thread(session: Session, csession: CSession, external_userid: str) -> AgentThread:
    existing = (
        session.query(AgentThread)
        .filter_by(open_kfid=csession.open_kfid, external_userid=external_userid)
        .one_or_none()
    )
    if existing is not None:
        existing.session_id = csession.id
        session.flush()
        return existing
    row = AgentThread(
        session_id=csession.id,
        open_kfid=csession.open_kfid,
        external_userid=external_userid,
        hermes_profile="cservice-assistant",
        uplink_pending=False,
        uplink_started_at=None,
        created_at=_now(),
    )
    session.add(row)
    session.flush()
    return row


def mark_uplink_pending(session: Session, thread: AgentThread) -> None:
    thread.uplink_pending = True
    thread.uplink_started_at = _now()
    session.flush()


def clear_uplink_pending(
    session: Session,
    *,
    thread_id: int | None = None,
    session_id: str | None = None,
) -> None:
    query = session.query(AgentThread)
    if thread_id is not None:
        row = query.filter_by(id=thread_id).one_or_none()
    elif session_id is not None:
        row = query.filter_by(session_id=session_id).one_or_none()
    else:
        return
    if row is None:
        return
    row.uplink_pending = False
    row.uplink_started_at = None
    session.flush()


def maybe_clear_uplink_timeout(session: Session, thread: AgentThread) -> None:
    """Lazy 30s timeout for generating state (§5.6 · CS-23)."""
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
        session.flush()
