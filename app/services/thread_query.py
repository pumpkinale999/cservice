"""Session thread serialization (§14 GET /customers/{id}/thread)."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.models import Draft, Message, Session as CSession
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
        }
    return {
        "session_id": session.id,
        "messages": [_message_to_dict(m) for m in messages],
        "pending_draft": pending_draft,
    }
