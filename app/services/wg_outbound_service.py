"""WeCom group outbound orchestration (§5.6 · D-P4-13 · P4-M2)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models import WgAuditLog, WgDraft, WgMessage, WgReplyAnchor, WgSession
from app.services.wecom_aibot_client import WecomAibotClient
from app.services.wecom_errors import CserviceWecomError
from app.services.wg_badge import on_round_cover_outbound


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


def _anchor_expired(anchor: WgReplyAnchor) -> bool:
    try:
        expires = datetime.fromisoformat(anchor.expires_at.replace("Z", "+00:00"))
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=UTC)
        return datetime.now(UTC) >= expires
    except ValueError:
        return True


def _get_draft(db: Session, draft_id: str) -> WgDraft:
    draft = db.get(WgDraft, draft_id)
    if draft is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="draft_not_found")
    return draft


def _raise_draft_conflict(draft: WgDraft) -> None:
    if draft.status == "superseded":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "draft_superseded", "message": "草稿已被新消息覆盖"},
        )
    if draft.status == "sent":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "draft_concurrent_conflict", "message": "该草稿已被其他接待发送"},
        )
    raise HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail={"code": "draft_not_pending", "message": "草稿不可发送"},
    )


def _claim_draft_for_send(db: Session, draft: WgDraft, expected_version: int) -> None:
    if draft.status != "pending":
        _raise_draft_conflict(draft)
    if draft.version != expected_version:
        _raise_draft_conflict(draft)
    updated = (
        db.query(WgDraft)
        .filter_by(id=draft.id, version=expected_version, status="pending")
        .update({"status": "sent"}, synchronize_session=False)
    )
    if updated == 0:
        db.expire(draft)
        fresh = db.get(WgDraft, draft.id)
        assert fresh is not None
        _raise_draft_conflict(fresh)
    db.expire(draft)


def _get_open_session(db: Session, chatid: str) -> WgSession:
    row = (
        db.query(WgSession)
        .filter_by(chatid=chatid, status="open")
        .order_by(WgSession.last_activity_at.desc())
        .first()
    )
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="session_not_found",
        )
    return row


def _get_session_for_send(db: Session, session_id: str) -> WgSession:
    csession = db.get(WgSession, session_id)
    if csession is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="session_not_found")
    if csession.status != "open":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="session_closed")
    return csession


def _get_anchor(db: Session, chatid: str) -> WgReplyAnchor:
    anchor = db.get(WgReplyAnchor, chatid)
    if anchor is None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="missing_anchor")
    if _anchor_expired(anchor):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="anchor_expired")
    return anchor


def _call_post_response(client: WecomAibotClient, response_url: str, content: str) -> dict[str, Any]:
    try:
        return client.post_response(response_url, content)
    except CserviceWecomError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={"code": "wecom_error", "errcode": exc.errcode, "errmsg": exc.errmsg},
        ) from exc


def _write_audit(
    db: Session,
    *,
    actor: str | None,
    action: str,
    chatid: str,
    session_id: str,
    draft_id: str | None = None,
    edited_text: str | None = None,
) -> None:
    db.add(
        WgAuditLog(
            actor_user_id=actor,
            chatid=chatid,
            session_id=session_id,
            action=action,
            draft_id=draft_id,
            edited_text=edited_text,
            created_at=_now(),
        )
    )


def send_text_to_group(
    db: Session,
    *,
    chatid: str,
    text: str,
    client: WecomAibotClient,
    actor_user_id: str | None = None,
) -> dict[str, Any]:
    """POST latest response_url and record outbound message (M1 skeleton)."""
    content = _validate_text(text)
    anchor = _get_anchor(db, chatid)
    session = _get_open_session(db, chatid)
    _call_post_response(client, anchor.response_url, content)

    now = _now()
    msg_id = str(uuid.uuid4())
    db.add(
        WgMessage(
            id=msg_id,
            session_id=session.id,
            direction="outbound",
            source_msgid=None,
            msg_type="text",
            content=content,
            sender_userid=None,
            sender_type="agent",
            delivery_status="sent",
            created_at=now,
        )
    )
    _write_audit(
        db,
        actor=actor_user_id,
        action="wg_send_text",
        chatid=chatid,
        session_id=session.id,
    )
    on_round_cover_outbound(session)
    session.last_activity_at = now

    return {
        "ok": True,
        "chatid": chatid,
        "session_id": session.id,
        "message_id": msg_id,
        "pending_reply_count": session.pending_reply_count,
    }


def send_wg_draft_as_agent(
    db: Session,
    *,
    draft_id: str,
    actor: str,
    client: WecomAibotClient,
    expected_version: int,
) -> dict[str, Any]:
    draft = _get_draft(db, draft_id)
    csession = _get_session_for_send(db, draft.session_id)
    content = _validate_text(draft.agent_text)
    _claim_draft_for_send(db, draft, expected_version)
    anchor = _get_anchor(db, csession.chatid)
    _call_post_response(client, anchor.response_url, content)

    now = _now()
    msg = WgMessage(
        id=str(uuid.uuid4()),
        session_id=csession.id,
        direction="outbound",
        source_msgid=None,
        msg_type="text",
        content=content,
        sender_userid=None,
        sender_type="agent",
        draft_id=draft.id,
        delivery_status="sent",
        created_at=now,
    )
    db.add(msg)
    _write_audit(
        db,
        actor=actor,
        action="wg_send_agent",
        chatid=csession.chatid,
        session_id=csession.id,
        draft_id=draft.id,
    )
    on_round_cover_outbound(csession)
    csession.last_activity_at = now
    db.flush()
    return {"message_id": msg.id, "delivery_status": "sent"}


def send_wg_draft_edited(
    db: Session,
    *,
    draft_id: str,
    actor: str,
    text: str,
    client: WecomAibotClient,
    expected_version: int,
) -> dict[str, Any]:
    draft = _get_draft(db, draft_id)
    csession = _get_session_for_send(db, draft.session_id)
    edited = _validate_text(text)
    agent_text = draft.agent_text
    _claim_draft_for_send(db, draft, expected_version)
    anchor = _get_anchor(db, csession.chatid)
    _call_post_response(client, anchor.response_url, edited)

    now = _now()
    db.add(
        WgMessage(
            id=str(uuid.uuid4()),
            session_id=csession.id,
            direction="outbound",
            source_msgid=None,
            msg_type="text",
            content=agent_text,
            sender_userid=None,
            sender_type="agent",
            draft_id=draft.id,
            delivery_status="draft_only",
            created_at=now,
        )
    )
    msg = WgMessage(
        id=str(uuid.uuid4()),
        session_id=csession.id,
        direction="outbound",
        source_msgid=None,
        msg_type="text",
        content=edited,
        sender_userid=None,
        sender_type="user",
        draft_id=draft.id,
        delivery_status="sent",
        created_at=now,
    )
    db.add(msg)
    _write_audit(
        db,
        actor=actor,
        action="wg_send_edited",
        chatid=csession.chatid,
        session_id=csession.id,
        draft_id=draft.id,
        edited_text=edited,
    )
    on_round_cover_outbound(csession)
    csession.last_activity_at = now
    db.flush()
    return {"message_id": msg.id, "delivery_status": "sent"}


def send_wg_manual(
    db: Session,
    *,
    session_id: str,
    actor: str,
    text: str,
    client: WecomAibotClient,
) -> dict[str, Any]:
    csession = _get_session_for_send(db, session_id)
    content = _validate_text(text)
    anchor = _get_anchor(db, csession.chatid)
    _call_post_response(client, anchor.response_url, content)

    now = _now()
    msg = WgMessage(
        id=str(uuid.uuid4()),
        session_id=csession.id,
        direction="outbound",
        source_msgid=None,
        msg_type="text",
        content=content,
        sender_userid=None,
        sender_type="user",
        draft_id=None,
        delivery_status="sent",
        created_at=now,
    )
    db.add(msg)
    _write_audit(
        db,
        actor=actor,
        action="wg_send_manual",
        chatid=csession.chatid,
        session_id=csession.id,
    )
    on_round_cover_outbound(csession)
    csession.last_activity_at = now
    db.flush()
    return {"message_id": msg.id, "delivery_status": "sent"}
