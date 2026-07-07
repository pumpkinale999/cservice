"""WeCom group Hermes uplink queue (§13 · CS-34)."""

from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from app.hermes import connection_registry
from app.hermes.schemas import CserviceGroupUplink
from app.models import WgGroup, WgSession
from app.services.wg_agent_thread import mark_uplink_pending
from app.services.wg_draft_service import supersede_pending_wg_drafts
from app.services.wg_uplink_context import build_wg_uplink_body, collect_pending_inbound_lines
from app.services.wg_uplink_retry import clear_wg_uplink_retry, due_wg_retries, record_wg_uplink_failure

logger = logging.getLogger(__name__)


def _build_uplink(
    db: Session,
    *,
    thread_id: int,
    session: WgSession,
    group: WgGroup,
    trigger_source_msgid: str,
    sender_userid: str | None = None,
) -> CserviceGroupUplink:
    pending_lines = collect_pending_inbound_lines(db, session.id)
    body = build_wg_uplink_body(
        db,
        session=session,
        group=group,
        pending_lines=pending_lines,
        latest_sender_userid=sender_userid,
    )
    return CserviceGroupUplink(
        thread_id=thread_id,
        session_id=session.id,
        ibot_id=group.ibot_id,
        chatid=group.chatid,
        body=body,
        trigger_source_msgid=trigger_source_msgid,
    )


def enqueue_wg_uplink(
    db: Session,
    *,
    session_id: str,
    thread_id: int,
    ibot_id: str,
    chatid: str,
    trigger_source_msgid: str,
    sender_userid: str | None = None,
    supersede: bool = True,
) -> None:
    if supersede:
        supersede_pending_wg_drafts(db, session_id, "new_inbound")
    from app.models import WgAgentThread

    thread = db.get(WgAgentThread, thread_id)
    if thread is not None:
        mark_uplink_pending(db, thread)
    session = db.get(WgSession, session_id)
    group = db.get(WgGroup, chatid)
    if session is None or group is None:
        logger.warning("wg uplink skipped missing session/group session=%s", session_id)
        return
    frame = _build_uplink(
        db,
        thread_id=thread_id,
        session=session,
        group=group,
        trigger_source_msgid=trigger_source_msgid,
        sender_userid=sender_userid,
    )
    if connection_registry.queue_outbound(frame.to_dict()):
        clear_wg_uplink_retry(db, session_id)
    else:
        record_wg_uplink_failure(
            db,
            session_id=session_id,
            thread_id=thread_id,
            trigger_source_msgid=trigger_source_msgid,
            body=frame.body,
            ibot_id=ibot_id,
            chatid=chatid,
            error="gateway_offline",
        )


async def flush_pending_wg_uplinks(
    db: Session,
    session_id: str | None = None,
    *,
    force_all: bool = False,
) -> int:
    if not connection_registry.is_cservice_group_gateway_registered():
        return 0
    from app.models import WgUplinkRetry

    if session_id is not None:
        row = db.get(WgUplinkRetry, session_id)
        rows = [row] if row is not None else []
    elif force_all:
        rows = db.query(WgUplinkRetry).all()
    else:
        rows = due_wg_retries(db)
    sent = 0
    for row in rows:
        frame = CserviceGroupUplink(
            thread_id=row.thread_id,
            session_id=row.session_id,
            ibot_id=row.ibot_id,
            chatid=row.chatid,
            body=row.body,
            trigger_source_msgid=row.trigger_source_msgid,
        )
        if connection_registry.queue_outbound(frame.to_dict()):
            clear_wg_uplink_retry(db, row.session_id)
            sent += 1
    sent += await connection_registry.drain_outbound(connection_registry.GROUP_ROLE)
    return sent
