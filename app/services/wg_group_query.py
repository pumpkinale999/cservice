"""WeCom group list query (§14.1 · CS-41 list visibility)."""

from __future__ import annotations

from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.models import WgGroup, WgMessage, WgSession


def _last_message_preview(db: Session, session_id: str) -> str | None:
    row = (
        db.query(WgMessage)
        .filter_by(session_id=session_id)
        .order_by(desc(WgMessage.created_at))
        .first()
    )
    if row is None or not row.content:
        return None
    text = str(row.content)
    return text[:120] if len(text) > 120 else text


def list_open_group_sessions(db: Session) -> list[dict]:
    """All open group sessions, newest activity first (public pool)."""
    rows = (
        db.query(WgSession, WgGroup)
        .join(WgGroup, WgSession.chatid == WgGroup.chatid)
        .filter(WgSession.status == "open", WgGroup.status == "active")
        .order_by(desc(WgSession.last_activity_at))
        .all()
    )
    out: list[dict] = []
    for session, group in rows:
        out.append(
            {
                "session_id": session.id,
                "chatid": session.chatid,
                "group_display_name": group.display_name,
                "pending_reply_count": session.pending_reply_count,
                "last_message_preview": _last_message_preview(db, session.id),
                "last_activity_at": session.last_activity_at,
            }
        )
    return out
