"""Hermes uplink queue (§15.3 · §15.5)."""

from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from app.hermes import connection_registry
from app.hermes.schemas import CserviceCustomerUplink
from app.services.draft_service import supersede_pending_drafts
from app.services.uplink_retry import clear_uplink_retry, due_retries, record_uplink_failure

logger = logging.getLogger(__name__)


def _build_uplink(
    *,
    thread_id: int,
    session_id: str,
    open_kfid: str,
    external_userid: str,
    text: str,
    trigger_wx_msgid: str,
) -> CserviceCustomerUplink:
    body = f"客户：{text}"
    return CserviceCustomerUplink(
        thread_id=thread_id,
        session_id=session_id,
        open_kfid=open_kfid,
        external_userid=external_userid,
        body=body,
        trigger_wx_msgid=trigger_wx_msgid,
    )


def enqueue_uplink(
    db: Session,
    *,
    session_id: str,
    thread_id: int,
    open_kfid: str,
    external_userid: str,
    text: str,
    trigger_wx_msgid: str,
    supersede: bool = True,
) -> None:
    """Enqueue uplink; persist to retry table if GW offline."""
    if supersede:
        supersede_pending_drafts(db, session_id, "new_inbound")
    frame = _build_uplink(
        thread_id=thread_id,
        session_id=session_id,
        open_kfid=open_kfid,
        external_userid=external_userid,
        text=text,
        trigger_wx_msgid=trigger_wx_msgid,
    )
    if connection_registry.queue_outbound(frame.to_dict()):
        clear_uplink_retry(db, session_id)
    else:
        record_uplink_failure(
            db,
            session_id=session_id,
            thread_id=thread_id,
            trigger_wx_msgid=trigger_wx_msgid,
            body=frame.body,
            open_kfid=open_kfid,
            external_userid=external_userid,
            error="gateway_offline",
        )


async def flush_pending_uplinks(
    db: Session,
    session_id: str | None = None,
    *,
    force_all: bool = False,
) -> int:
    """Retry uplink rows after GW connects."""
    if not connection_registry.is_cservice_gateway_registered():
        return 0
    from app.models import UplinkRetry

    if session_id is not None:
        row = db.get(UplinkRetry, session_id)
        rows = [row] if row is not None else []
    elif force_all:
        rows = db.query(UplinkRetry).all()
    else:
        rows = due_retries(db)
    sent = 0
    for row in rows:
        frame = CserviceCustomerUplink(
            thread_id=row.thread_id,
            session_id=row.session_id,
            open_kfid=row.open_kfid,
            external_userid=row.external_userid,
            body=row.body,
            trigger_wx_msgid=row.trigger_wx_msgid,
        )
        if connection_registry.queue_outbound(frame.to_dict()):
            clear_uplink_retry(db, row.session_id)
            sent += 1
    sent += await connection_registry.drain_outbound()
    return sent
