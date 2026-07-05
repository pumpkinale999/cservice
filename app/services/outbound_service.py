"""Outbound send_msg orchestration (§17.3 · M4)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models import AuditLog, Customer, Draft, Message, Session as CSession
from app.services.badge import on_round_cover_outbound
from app.services.session_auth import require_session_open, require_session_servicer
from app.services.wecom_errors import CserviceWecomError
from app.services.wecom_kf_client import WecomKfClient


def _now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def _validate_text(text: str) -> str:
    content = (text or "").strip()
    if not content:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="empty_text",
        )
    return content


def _get_draft_pending(db: Session, draft_id: str) -> Draft:
    draft = db.get(Draft, draft_id)
    if draft is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="draft_not_found")
    if draft.status != "pending":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="draft_not_pending")
    return draft


def _get_session_for_send(db: Session, session_id: str, actor: str) -> tuple[CSession, Customer]:
    csession = db.get(CSession, session_id)
    if csession is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="session_not_found")
    require_session_servicer(csession, actor)
    require_session_open(csession)
    customer = db.get(Customer, csession.customer_id)
    if customer is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="customer_not_found")
    return csession, customer


def _call_send_msg(
    client: WecomKfClient,
    open_kfid: str,
    external_userid: str,
    content: str,
) -> dict[str, Any]:
    try:
        return client.send_text_msg(open_kfid, external_userid, content)
    except CserviceWecomError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={"wx_errcode": exc.errcode, "wx_errmsg": exc.errmsg},
        ) from exc


def _write_audit(
    db: Session,
    *,
    actor: str,
    action: str,
    draft_id: str | None = None,
    edited_text: str | None = None,
) -> None:
    db.add(
        AuditLog(
            actor_user_id=actor,
            action=action,
            draft_id=draft_id,
            edited_text=edited_text,
            created_at=_now(),
        )
    )


def send_draft_as_agent(
    db: Session,
    *,
    draft_id: str,
    actor: str,
    client: WecomKfClient,
) -> dict[str, Any]:
    draft = _get_draft_pending(db, draft_id)
    csession, customer = _get_session_for_send(db, draft.session_id, actor)
    content = _validate_text(draft.agent_text)
    result = _call_send_msg(client, csession.open_kfid, customer.external_userid, content)
    wx_msgid = str(result.get("msgid") or f"local-{uuid.uuid4()}")
    msg = Message(
        id=str(uuid.uuid4()),
        session_id=csession.id,
        direction="outbound",
        wx_msgid=wx_msgid,
        msg_type="text",
        content=content,
        sender_type="agent",
        draft_id=draft.id,
        delivery_status="sent",
        created_at=_now(),
    )
    db.add(msg)
    draft.status = "sent"
    _write_audit(db, actor=actor, action="send_agent", draft_id=draft.id)
    on_round_cover_outbound(csession)
    db.flush()
    return {"message_id": msg.id, "wx_msgid": wx_msgid, "delivery_status": "sent"}


def send_draft_edited(
    db: Session,
    *,
    draft_id: str,
    actor: str,
    text: str,
    client: WecomKfClient,
) -> dict[str, Any]:
    draft = _get_draft_pending(db, draft_id)
    csession, customer = _get_session_for_send(db, draft.session_id, actor)
    edited = _validate_text(text)
    result = _call_send_msg(client, csession.open_kfid, customer.external_userid, edited)
    wx_msgid = str(result.get("msgid") or f"local-{uuid.uuid4()}")
    db.add(
        Message(
            id=str(uuid.uuid4()),
            session_id=csession.id,
            direction="outbound",
            wx_msgid=None,
            msg_type="text",
            content=draft.agent_text,
            sender_type="agent",
            draft_id=draft.id,
            delivery_status="draft_only",
            created_at=_now(),
        )
    )
    msg = Message(
        id=str(uuid.uuid4()),
        session_id=csession.id,
        direction="outbound",
        wx_msgid=wx_msgid,
        msg_type="text",
        content=edited,
        sender_type="user",
        draft_id=draft.id,
        delivery_status="sent",
        created_at=_now(),
    )
    db.add(msg)
    draft.status = "sent"
    _write_audit(
        db,
        actor=actor,
        action="send_edited",
        draft_id=draft.id,
        edited_text=edited,
    )
    on_round_cover_outbound(csession)
    db.flush()
    return {"message_id": msg.id, "wx_msgid": wx_msgid, "delivery_status": "sent"}


def send_manual(
    db: Session,
    *,
    session_id: str,
    actor: str,
    text: str,
    client: WecomKfClient,
) -> dict[str, Any]:
    csession, customer = _get_session_for_send(db, session_id, actor)
    content = _validate_text(text)
    result = _call_send_msg(client, csession.open_kfid, customer.external_userid, content)
    wx_msgid = str(result.get("msgid") or f"local-{uuid.uuid4()}")
    msg = Message(
        id=str(uuid.uuid4()),
        session_id=csession.id,
        direction="outbound",
        wx_msgid=wx_msgid,
        msg_type="text",
        content=content,
        sender_type="user",
        draft_id=None,
        delivery_status="sent",
        created_at=_now(),
    )
    db.add(msg)
    _write_audit(db, actor=actor, action="send_manual")
    on_round_cover_outbound(csession)
    db.flush()
    return {"message_id": msg.id, "wx_msgid": wx_msgid, "delivery_status": "sent"}
