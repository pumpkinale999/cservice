"""Assign retry queue (§21.3)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from app.models import AssignRetry, Session as CSession

BACKOFF_SECONDS = (30, 120, 600, 600, 600)
MAX_ATTEMPTS = 5


def _now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def _next_retry_at(attempts: int) -> str:
    idx = min(attempts, len(BACKOFF_SECONDS) - 1)
    return (datetime.now(UTC) + timedelta(seconds=BACKOFF_SECONDS[idx])).isoformat()


def record_assign_failure(session: Session, csession: CSession, errcode: int) -> None:
    session.flush()  # same-batch duplicate msg must see pending AssignRetry row
    row = session.get(AssignRetry, csession.id)
    if row is None:
        row = AssignRetry(
            session_id=csession.id,
            attempts=1,
            next_retry_at=_next_retry_at(0),
            last_errcode=errcode,
        )
        session.add(row)
    else:
        row.attempts += 1
        row.last_errcode = errcode
        row.next_retry_at = _next_retry_at(row.attempts)
    if row.attempts >= MAX_ATTEMPTS:
        csession.status = "unassigned"
        csession.servicer_userid = None


def clear_assign_retry(session: Session, session_id: str) -> None:
    row = session.get(AssignRetry, session_id)
    if row is not None:
        session.delete(row)
