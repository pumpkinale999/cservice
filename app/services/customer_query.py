"""Customer list query (§14 GET /customers)."""

from __future__ import annotations

from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.models import Customer, KfAccount, Message, Session as CSession


def _last_message_preview(db: Session, session_id: str) -> str | None:
    row = (
        db.query(Message)
        .filter_by(session_id=session_id)
        .order_by(desc(Message.created_at))
        .first()
    )
    if row is None or not row.content:
        return None
    text = str(row.content)
    return text[:120] if len(text) > 120 else text


def list_open_customer_sessions(db: Session) -> list[dict]:
    """All non-closed sessions (public pool), newest activity first."""
    rows = (
        db.query(CSession, Customer, KfAccount)
        .join(Customer, CSession.customer_id == Customer.id)
        .join(KfAccount, CSession.open_kfid == KfAccount.open_kfid)
        .filter(CSession.status.in_(("open", "unassigned")))
        .order_by(desc(CSession.last_activity_at))
        .all()
    )
    out: list[dict] = []
    for csession, customer, account in rows:
        scene = customer.last_scene or customer.first_scene
        out.append(
            {
                "session_id": csession.id,
                "customer_display_name": customer.display_name or customer.external_userid,
                "kf_account_short_name": account.display_name,
                "scene": scene,
                "pending_reply_count": csession.pending_reply_count,
                "last_message_preview": _last_message_preview(db, csession.id),
                "last_activity_at": csession.last_activity_at,
            }
        )
    return out
