"""Session thread serialization (§14 GET /customers/{id}/thread · CS-23)."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.models import AgentThread, Draft, Message, Session as CSession
from app.services.agent_thread import maybe_clear_uplink_timeout
from app.services.badge import fail_type_label


def _message_to_dict(msg: Message) -> dict:
    direction = msg.direction
    item: dict = {
        "id": msg.id,
        "direction": direction,
        "content": msg.content or "",
        "msg_type": msg.msg_type,
        "created_at": msg.created_at,
    }
    if direction == "outbound":
        item["sender_type"] = msg.sender_type
        item["delivery_status"] = msg.delivery_status
        if msg.delivery_status == "failed" and msg.wx_fail_type is not None:
            item["delivery_error"] = fail_type_label(int(msg.wx_fail_type))
        if msg.draft_id:
            item["draft_id"] = msg.draft_id
    return item


def get_thread_for_session(db: Session, session: CSession) -> dict:
    messages = (
        db.query(Message)
        .filter_by(session_id=session.id)
        .order_by(Message.created_at.asc())
        .all()
    )
    pending = (
        db.query(Draft)
        .filter_by(session_id=session.id, status="pending")
        .order_by(Draft.created_at.desc())
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
        db.query(AgentThread)
        .filter_by(session_id=session.id)
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
        "thread_id": thread_id,
        "uplink_pending": uplink_pending,
        "uplink_started_at": uplink_started_at,
        "messages": [_message_to_dict(m) for m in messages],
        "pending_draft": pending_draft,
    }
