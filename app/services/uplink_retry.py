"""Uplink retry persistence (§15.5)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from app.models import UplinkRetry

BACKOFF_SECONDS = (30, 120, 600, 600, 600)
MAX_ATTEMPTS = 5


def _now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def _next_retry_at(attempts: int) -> str:
    idx = min(attempts, len(BACKOFF_SECONDS) - 1)
    return (datetime.now(UTC) + timedelta(seconds=BACKOFF_SECONDS[idx])).isoformat()


def record_uplink_failure(
    db: Session,
    *,
    session_id: str,
    thread_id: int,
    trigger_wx_msgid: str,
    body: str,
    open_kfid: str,
    external_userid: str,
    error: str,
) -> None:
    row = db.get(UplinkRetry, session_id)
    if row is None:
        row = UplinkRetry(
            session_id=session_id,
            thread_id=thread_id,
            trigger_wx_msgid=trigger_wx_msgid,
            body=body,
            open_kfid=open_kfid,
            external_userid=external_userid,
            attempts=1,
            next_retry_at=_now(),
            last_error=error,
        )
        db.add(row)
    else:
        row.thread_id = thread_id
        row.trigger_wx_msgid = trigger_wx_msgid
        row.body = body
        row.open_kfid = open_kfid
        row.external_userid = external_userid
        row.attempts += 1
        row.last_error = error
        row.next_retry_at = _next_retry_at(row.attempts)


def clear_uplink_retry(db: Session, session_id: str) -> None:
    row = db.get(UplinkRetry, session_id)
    if row is not None:
        db.delete(row)


def due_retries(db: Session) -> list[UplinkRetry]:
    now = _now()
    return (
        db.query(UplinkRetry)
        .filter(UplinkRetry.attempts < MAX_ATTEMPTS)
        .filter(
            (UplinkRetry.next_retry_at.is_(None)) | (UplinkRetry.next_retry_at <= now)
        )
        .all()
    )
