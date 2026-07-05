"""Single message ingest from sync_msg (§21.2 steps 1-3/3b)."""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from app.models import AuditLog, Customer, Draft, Message, Session as CSession
from app.services.badge import on_round_cover_outbound, on_text_inbound

PLACEHOLDER_NON_TEXT = "[暂不支持该类型，请人工在其它渠道处理]"
ORIGIN5_NOTE = "（经企微客户端发送）"


def _now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def _get_or_create_customer(
    db: Session,
    external_userid: str,
    scene: str | None,
) -> Customer:
    row = db.query(Customer).filter_by(external_userid=external_userid).one_or_none()
    if row is None:
        row = Customer(
            id=str(uuid.uuid4()),
            external_userid=external_userid,
            display_name=external_userid,
            first_scene=scene,
            last_scene=scene,
            created_at=_now(),
        )
        db.add(row)
        db.flush()
    else:
        if scene:
            row.last_scene = scene
    return row


def _get_or_create_open_session(
    db: Session,
    open_kfid: str,
    customer: Customer,
) -> CSession:
    row = (
        db.query(CSession)
        .filter_by(open_kfid=open_kfid, customer_id=customer.id)
        .filter(CSession.status != "closed")
        .order_by(CSession.last_activity_at.desc())
        .first()
    )
    if row is None:
        row = CSession(
            id=str(uuid.uuid4()),
            open_kfid=open_kfid,
            customer_id=customer.id,
            servicer_userid=None,
            status="open",
            pending_reply_count=0,
            last_activity_at=_now(),
        )
        db.add(row)
        db.flush()
    return row


def _supersede_pending_drafts(db: Session, session_id: str, reason: str) -> None:
    pending = (
        db.query(Draft)
        .filter_by(session_id=session_id, status="pending")
        .all()
    )
    for d in pending:
        d.status = "superseded"
        d.superseded_reason = reason


def ingest_sync_message(
    db: Session,
    item: dict[str, Any],
    open_kfid: str,
) -> tuple[CSession, Customer, bool]:
    """Returns (session, customer, is_new_inbound). is_new_inbound=False if duplicate wx_msgid."""
    wx_msgid = str(item.get("msgid", ""))
    if not wx_msgid:
        raise ValueError("missing msgid")

    existing = db.query(Message).filter_by(wx_msgid=wx_msgid).one_or_none()
    if existing is not None:
        csession = db.get(CSession, existing.session_id)
        customer = db.get(Customer, csession.customer_id) if csession else None
        assert csession and customer
        return csession, customer, False

    external_userid = str(item.get("external_userid", ""))
    scene = item.get("scene") or item.get("scene_param")
    scene_str = str(scene) if scene else None
    customer = _get_or_create_customer(db, external_userid, scene_str)
    csession = _get_or_create_open_session(db, open_kfid, customer)

    origin = int(item.get("origin", 3))
    msgtype = str(item.get("msgtype", "text"))
    send_time = item.get("send_time")
    csession.last_activity_at = _now()

    if origin == 5:
        content = _extract_text(item)
        if ORIGIN5_NOTE not in content:
            content = f"{content} {ORIGIN5_NOTE}".strip()
        db.add(
            Message(
                id=str(uuid.uuid4()),
                session_id=csession.id,
                direction="outbound",
                wx_msgid=wx_msgid,
                msg_type=msgtype,
                content=content,
                sender_type="user",
                delivery_status="sent",
                created_at=_now(),
            )
        )
        on_round_cover_outbound(csession)
        _supersede_pending_drafts(db, csession.id, "origin=5")
        db.add(
            AuditLog(
                actor_user_id=None,
                action="send_wecom_client",
                draft_id=None,
                edited_text=None,
                created_at=_now(),
            )
        )
        return csession, customer, True

    # origin=3 inbound
    if msgtype == "text":
        content = _extract_text(item)
    else:
        content = PLACEHOLDER_NON_TEXT

    db.add(
        Message(
            id=str(uuid.uuid4()),
            session_id=csession.id,
            direction="inbound",
            wx_msgid=wx_msgid,
            msg_type=msgtype,
            content=content,
            sender_type="customer",
            created_at=_now(),
        )
    )

    if origin == 3 and msgtype == "text":
        on_text_inbound(csession)

    return csession, customer, True


def _extract_text(item: dict[str, Any]) -> str:
    text_obj = item.get("text") or {}
    if isinstance(text_obj, dict):
        return str(text_obj.get("content", ""))
    return str(text_obj)


def message_item_scene(item: dict[str, Any]) -> str | None:
    scene = item.get("scene") or item.get("scene_param")
    return str(scene) if scene else None
