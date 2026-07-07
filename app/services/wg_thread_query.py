"""WeCom group session thread serialization (§14 · P4-M2)."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.models import WgAgentThread, WgDraft, WgMessage, WgSession
from app.services.wg_agent_thread import maybe_clear_uplink_timeout


def _message_to_dict(msg: WgMessage) -> dict:
    item: dict = {
        "id": msg.id,
        "direction": msg.direction,
        "content": msg.content or "",
        "msg_type": msg.msg_type,
        "created_at": msg.created_at,
    }
    if msg.direction == "inbound":
        item["sender_userid"] = msg.sender_userid
    if msg.direction == "outbound":
        item["sender_type"] = msg.sender_type
        item["delivery_status"] = msg.delivery_status
        if msg.draft_id:
            item["draft_id"] = msg.draft_id
    return item


def get_wg_thread_for_session(db: Session, session: WgSession) -> dict:
    messages = (
        db.query(WgMessage)
        .filter_by(session_id=session.id)
        .order_by(WgMessage.created_at.asc())
        .all()
    )
    pending = (
        db.query(WgDraft)
        .filter_by(session_id=session.id, status="pending")
        .order_by(WgDraft.created_at.desc())
        .first()
    )
    pending_draft = None
    if pending is not None:
        pending_draft = {
            "id": pending.id,
            "agent_text": pending.agent_text,
            "status": pending.status,
            "version": pending.version,
        }

    thread = (
        db.query(WgAgentThread)
        .filter_by(chatid=session.chatid)
        .one_or_none()
    )
    thread_id = None
    uplink_pending = False
    uplink_started_at = None
    if thread is not None:
        maybe_clear_uplink_timeout(db, thread)
        thread_id = thread.id
        uplink_pending = bool(thread.uplink_pending)
        uplink_started_at = thread.uplink_started_at

    return {
        "session_id": session.id,
        "chatid": session.chatid,
        "thread_id": thread_id,
        "uplink_pending": uplink_pending,
        "uplink_started_at": uplink_started_at,
        "messages": [_message_to_dict(m) for m in messages],
        "pending_draft": pending_draft,
    }
