"""Ensure cservice_agent_thread after assign (§21.2 step 5)."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.models import AgentThread, Session as CSession


def _now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def ensure_agent_thread(session: Session, csession: CSession, external_userid: str) -> AgentThread:
    existing = (
        session.query(AgentThread).filter_by(session_id=csession.id).one_or_none()
    )
    if existing is not None:
        return existing
    row = AgentThread(
        session_id=csession.id,
        open_kfid=csession.open_kfid,
        external_userid=external_userid,
        hermes_profile="cservice-assistant",
        created_at=_now(),
    )
    session.add(row)
    session.flush()
    return row
