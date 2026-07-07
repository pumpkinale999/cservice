"""WeCom group uplink hook — trigger after ingress (P4-M2)."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.hermes.wg_uplink_queue import enqueue_wg_uplink
from app.models import WgGroup, WgSession
from app.services.wg_agent_thread import ensure_wg_agent_thread


def trigger_wg_uplink_after_ingress(
    db: Session,
    *,
    session: WgSession,
    group: WgGroup,
    trigger_source_msgid: str,
    sender_userid: str,
) -> None:
    thread = ensure_wg_agent_thread(
        db,
        ibot_id=group.ibot_id,
        chatid=group.chatid,
        session=session,
    )
    enqueue_wg_uplink(
        db,
        session_id=session.id,
        thread_id=thread.id,
        ibot_id=group.ibot_id,
        chatid=group.chatid,
        trigger_source_msgid=trigger_source_msgid,
        sender_userid=sender_userid,
        supersede=True,
    )
