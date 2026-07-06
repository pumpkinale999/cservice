"""Ingress filtering for sync_msg (§21.2 step 0 · D-CS-21 · CS-21)."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from app.models import EventLog

_SYSTEM_EVENT_TYPES = frozenset({"enter_session", "session_status_change"})


def _now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def valid_external_userid(external_userid: str | None) -> bool:
    return bool((external_userid or "").strip())


def log_system_event(
    db: Session,
    *,
    open_kfid: str,
    event_type: str,
    external_userid: str | None,
    payload: dict[str, Any],
) -> None:
    db.add(
        EventLog(
            open_kfid=open_kfid,
            event_type=event_type,
            external_userid=external_userid or None,
            payload_json=json.dumps(payload, ensure_ascii=False),
            created_at=_now(),
        )
    )


def should_skip_customer_ingress(item: dict[str, Any]) -> bool:
    """True when item must not upsert customer/session/message (§21.2 step 0)."""
    if not valid_external_userid(str(item.get("external_userid", ""))):
        return True
    event_type = str(item.get("event_type") or "").strip()
    if event_type in _SYSTEM_EVENT_TYPES:
        return True
    return False


def record_skipped_ingress(db: Session, item: dict[str, Any], open_kfid: str) -> None:
    event_type = str(item.get("event_type") or "invalid_external_userid").strip()
    if not event_type:
        event_type = "invalid_external_userid"
    log_system_event(
        db,
        open_kfid=open_kfid,
        event_type=event_type,
        external_userid=str(item.get("external_userid", "") or "") or None,
        payload=item,
    )
