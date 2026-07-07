"""WeCom group uplink retry persistence (§15.5)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from app.models import WgUplinkRetry

BACKOFF_SECONDS = (30, 120, 600, 600, 600)
MAX_ATTEMPTS = 5


def _now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def _next_retry_at(attempts: int) -> str:
    idx = min(attempts, len(BACKOFF_SECONDS) - 1)
    return (datetime.now(UTC) + timedelta(seconds=BACKOFF_SECONDS[idx])).isoformat()


def record_wg_uplink_failure(
    db: Session,
    *,
    session_id: str,
    thread_id: int,
    trigger_source_msgid: str,
    body: str,
    ibot_id: str,
    chatid: str,
    error: str,
) -> None:
    row = db.get(WgUplinkRetry, session_id)
    if row is None:
        row = WgUplinkRetry(
            session_id=session_id,
            thread_id=thread_id,
            trigger_source_msgid=trigger_source_msgid,
            body=body,
            ibot_id=ibot_id,
            chatid=chatid,
            attempts=1,
            next_retry_at=_now(),
            last_error=error,
        )
        db.add(row)
    else:
        row.thread_id = thread_id
        row.trigger_source_msgid = trigger_source_msgid
        row.body = body
        row.ibot_id = ibot_id
        row.chatid = chatid
        row.attempts += 1
        row.last_error = error
        row.next_retry_at = _next_retry_at(row.attempts)


def clear_wg_uplink_retry(db: Session, session_id: str) -> None:
    row = db.get(WgUplinkRetry, session_id)
    if row is not None:
        db.delete(row)


def due_wg_retries(db: Session) -> list[WgUplinkRetry]:
    now = _now()
    return (
        db.query(WgUplinkRetry)
        .filter(WgUplinkRetry.attempts < MAX_ATTEMPTS)
        .filter(
            (WgUplinkRetry.next_retry_at.is_(None)) | (WgUplinkRetry.next_retry_at <= now)
        )
        .all()
    )
