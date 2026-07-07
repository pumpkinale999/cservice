"""WeCom group internal ingress (§5.4 · CS-29 · CS-40 · CS-41)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.models import (
    WgGroup,
    WgIngressDedup,
    WgMessage,
    WgReplyAnchor,
    WgSession,
)
from app.services.wg_badge import on_text_inbound
from app.services.wg_uplink_hook import trigger_wg_uplink_after_ingress
from app.services.wg_ingress_filter import is_non_text_ingress, log_non_text_ignored

ANCHOR_TTL_SECONDS = 3600


class WgIngressDisabledError(Exception):
    pass


class WgUnknownGroupError(Exception):
    pass


def _now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def _default_expires_at() -> str:
    return (
        datetime.now(UTC).replace(microsecond=0) + timedelta(seconds=ANCHOR_TTL_SECONDS)
    ).isoformat()


def _extract_text(payload: dict[str, Any]) -> str:
    text = payload.get("text")
    if isinstance(text, dict):
        return str(text.get("content") or "").strip()
    return str(text or "").strip()


def _display_name(payload: dict[str, Any], chatid: str) -> str:
    name = str(payload.get("group_display_name") or "").strip()
    if name:
        return name
    suffix = chatid[-8:] if len(chatid) > 8 else chatid
    return f"群·{suffix}"


def _dedup_key(ibot_id: str, msgid: str) -> str:
    return f"{ibot_id}:{msgid}"


def _ensure_wg_enabled(settings: Settings | None = None) -> Settings:
    cfg = settings or get_settings()
    if not cfg.cservice_wg_enabled:
        raise WgIngressDisabledError()
    return cfg


def _get_or_create_group(
    db: Session,
    *,
    chatid: str,
    ibot_id: str,
    payload: dict[str, Any],
    auto_register: bool,
) -> tuple[WgGroup, bool]:
    row = db.get(WgGroup, chatid)
    if row is not None:
        if row.status == "disabled":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="group_disabled",
            )
        return row, False
    if not auto_register:
        raise WgUnknownGroupError()
    row = WgGroup(
        chatid=chatid,
        ibot_id=ibot_id,
        display_name=_display_name(payload, chatid),
        status="active",
        created_at=_now(),
    )
    db.add(row)
    db.flush()
    return row, True


def _get_or_create_open_session(db: Session, chatid: str) -> WgSession:
    row = (
        db.query(WgSession)
        .filter_by(chatid=chatid, status="open")
        .order_by(WgSession.last_activity_at.desc())
        .first()
    )
    if row is not None:
        return row
    row = WgSession(
        id=str(uuid.uuid4()),
        chatid=chatid,
        status="open",
        pending_reply_count=0,
        last_activity_at=_now(),
    )
    db.add(row)
    db.flush()
    return row


def _upsert_anchor(
    db: Session,
    *,
    chatid: str,
    response_url: str,
    source_msgid: str,
    expires_at: str | None,
) -> None:
    row = db.get(WgReplyAnchor, chatid)
    exp = (expires_at or "").strip() or _default_expires_at()
    now = _now()
    if row is None:
        db.add(
            WgReplyAnchor(
                chatid=chatid,
                response_url=response_url,
                expires_at=exp,
                source_msgid=source_msgid,
                updated_at=now,
            )
        )
    else:
        row.response_url = response_url
        row.expires_at = exp
        row.source_msgid = source_msgid
        row.updated_at = now


def handle_wecom_group_ingress(
    db: Session,
    payload: dict[str, Any],
    *,
    settings: Settings | None = None,
) -> dict[str, Any]:
    """Persist normalized aibot group @ event; returns result dict."""
    cfg = _ensure_wg_enabled(settings)

    chattype = str(payload.get("chattype") or "").strip().lower()
    if chattype and chattype != "group":
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="invalid_chattype",
        )

    ibot_id = str(payload.get("ibot_id") or "").strip()
    chatid = str(payload.get("chatid") or "").strip()
    msgid = str(payload.get("msgid") or "").strip()
    sender_userid = str(payload.get("sender_userid") or "").strip()
    response_url = str(payload.get("response_url") or "").strip()

    missing = [
        name
        for name, val in (
            ("ibot_id", ibot_id),
            ("chatid", chatid),
            ("msgid", msgid),
            ("sender_userid", sender_userid),
            ("response_url", response_url),
        )
        if not val
    ]
    if missing:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"code": "missing_fields", "fields": missing},
        )

    if is_non_text_ingress(payload):
        log_non_text_ignored(
            chatid=chatid,
            msgid=msgid,
            msgtype=str(payload.get("msgtype") or payload.get("msg_type") or ""),
        )
        return {"ok": True, "ignored": True, "reason": "non_text"}

    dedup = _dedup_key(ibot_id, msgid)
    if db.get(WgIngressDedup, dedup) is not None:
        return {"ok": True, "duplicate": True, "msgid": msgid}

    existing_msg = (
        db.query(WgMessage).filter_by(source_msgid=msgid).one_or_none()
    )
    if existing_msg is not None:
        return {"ok": True, "duplicate": True, "msgid": msgid}

    try:
        group, created = _get_or_create_group(
            db,
            chatid=chatid,
            ibot_id=ibot_id,
            payload=payload,
            auto_register=cfg.cservice_wg_auto_register,
        )
    except WgUnknownGroupError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="unknown_group",
        ) from exc

    session = _get_or_create_open_session(db, chatid)
    text = _extract_text(payload)
    now = _now()

    db.add(
        WgMessage(
            id=str(uuid.uuid4()),
            session_id=session.id,
            direction="inbound",
            source_msgid=msgid,
            msg_type="text",
            content=text,
            sender_userid=sender_userid,
            sender_type="user",
            delivery_status="received",
            created_at=now,
        )
    )
    db.add(WgIngressDedup(dedup_key=dedup, processed_at=now))

    expires_at = str(payload.get("expires_at") or "").strip() or None
    _upsert_anchor(
        db,
        chatid=chatid,
        response_url=response_url,
        source_msgid=msgid,
        expires_at=expires_at,
    )

    on_text_inbound(session)
    session.last_activity_at = now

    trigger_wg_uplink_after_ingress(
        db,
        session=session,
        group=group,
        trigger_source_msgid=msgid,
        sender_userid=sender_userid,
    )

    return {
        "ok": True,
        "chatid": chatid,
        "session_id": session.id,
        "group_display_name": group.display_name,
        "pending_reply_count": session.pending_reply_count,
        "auto_registered": created,
    }
