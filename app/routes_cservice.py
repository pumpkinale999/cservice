"""REST routes — cservice domain API (M1 health · M4 customers/drafts)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated

from sqlalchemy import func, select

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.api.deps import require_service_auth
from app.config import get_settings
from app.db import db_ok, get_session_factory, table_exists
from app.hermes.connection_registry import (
    is_cservice_gateway_registered,
    is_cservice_group_gateway_registered,
)
from app.models import KfAccount, Session as CSession, SyncState, WgSession
from app.services.customer_query import list_open_customer_sessions
from app.services.outbound_service import (
    send_draft_as_agent,
    send_draft_edited,
    send_manual,
)
from app.services.session_auth import require_session_servicer
from app.services.thread_query import get_thread_for_session
from app.services.wecom_aibot_client import WecomAibotClient
from app.services.wecom_kf_client import WecomKfClient, probe_wecom_token
from app.services.wg_group_query import list_open_group_sessions
from app.services.wg_outbound_service import (
    send_wg_draft_as_agent,
    send_wg_draft_edited,
    send_wg_manual,
)
from app.services.wg_thread_query import get_wg_thread_for_session

router = APIRouter(prefix="/cservice", tags=["cservice"])


class SendEditedBody(BaseModel):
    text: str
    expected_version: int


class SendDraftBody(BaseModel):
    expected_version: int


class SendManualBody(BaseModel):
    text: str


def _wecom_client() -> WecomKfClient:
    return WecomKfClient()


def _aibot_client() -> WecomAibotClient:
    return WecomAibotClient()


def _require_wg_enabled() -> None:
    if not get_settings().cservice_wg_enabled:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="wg_disabled",
        )


def _sync_cursor_age_seconds(session) -> int | None:
    row = session.query(SyncState).order_by(SyncState.updated_at.asc()).first()
    if row is None or not row.updated_at:
        return None
    try:
        updated = datetime.fromisoformat(row.updated_at.replace("Z", "+00:00"))
        if updated.tzinfo is None:
            updated = updated.replace(tzinfo=UTC)
        return max(0, int((datetime.now(UTC) - updated).total_seconds()))
    except ValueError:
        return None


@router.get("/health")
def cservice_health() -> dict:
    """Health probe — skstudio docs/cservice-产品设计.md §26.4."""
    settings = get_settings()
    wecom_configured = settings.wecom_configured()
    db = db_ok() and table_exists("cservice_kf_account")
    open_kfid_count = None
    sync_cursor_age_seconds = None
    wecom_token = "not_configured"
    if wecom_configured:
        wecom_token = probe_wecom_token(settings)
    ok = db and wecom_token != "error"
    wg_ingress = (
        settings.cservice_wg_enabled and db and table_exists("cservice_wg_group")
    )
    if db:
        factory = get_session_factory()
        session = factory()
        try:
            open_kfid_count = session.scalar(select(func.count()).select_from(KfAccount))
            sync_cursor_age_seconds = _sync_cursor_age_seconds(session)
        finally:
            session.close()
    return {
        "ok": ok,
        "enabled": True,
        "db": db,
        "wecom_configured": wecom_configured,
        "wecom_token": wecom_token if wecom_configured else None,
        "sync_cursor_age_seconds": sync_cursor_age_seconds,
        "hermes_cservice_gateway": is_cservice_gateway_registered(),
        "wecom_group_ingress": wg_ingress,
        "wecom_group_assistant_gateway": is_cservice_group_gateway_registered(),
        "open_kfid_count": open_kfid_count,
        "service": "cservice",
    }


@router.get("/customers")
def list_customers(
    actor_user_id: Annotated[str, Depends(require_service_auth)],
) -> dict:
    """All open customer sessions — public pool (§14)."""
    _ = actor_user_id  # auth only; list is not filtered by servicer
    factory = get_session_factory()
    db = factory()
    try:
        items = list_open_customer_sessions(db)
        return {"customers": items}
    finally:
        db.close()


@router.get("/customers/{session_id}/thread")
def get_customer_thread(
    session_id: str,
    actor_user_id: Annotated[str, Depends(require_service_auth)],
) -> dict:
    """Message thread + pending draft (§14)."""
    factory = get_session_factory()
    db = factory()
    try:
        csession = db.get(CSession, session_id)
        if csession is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="session_not_found",
            )
        require_session_servicer(csession, actor_user_id)
        return get_thread_for_session(db, csession)
    finally:
        db.close()


@router.post("/drafts/{draft_id}/send")
def post_draft_send(
    draft_id: str,
    body: SendDraftBody,
    actor_user_id: Annotated[str, Depends(require_service_auth)],
) -> dict:
    factory = get_session_factory()
    db = factory()
    client = _wecom_client()
    try:
        result = send_draft_as_agent(
            db,
            draft_id=draft_id,
            actor=actor_user_id,
            client=client,
            expected_version=body.expected_version,
        )
        db.commit()
        return result
    finally:
        client.close()
        db.close()


@router.post("/drafts/{draft_id}/send-edited")
def post_draft_send_edited(
    draft_id: str,
    body: SendEditedBody,
    actor_user_id: Annotated[str, Depends(require_service_auth)],
) -> dict:
    factory = get_session_factory()
    db = factory()
    client = _wecom_client()
    try:
        result = send_draft_edited(
            db,
            draft_id=draft_id,
            actor=actor_user_id,
            text=body.text,
            client=client,
            expected_version=body.expected_version,
        )
        db.commit()
        return result
    finally:
        client.close()
        db.close()


@router.post("/customers/{session_id}/send-manual")
def post_send_manual(
    session_id: str,
    body: SendManualBody,
    actor_user_id: Annotated[str, Depends(require_service_auth)],
) -> dict:
    factory = get_session_factory()
    db = factory()
    client = _wecom_client()
    try:
        result = send_manual(
            db,
            session_id=session_id,
            actor=actor_user_id,
            text=body.text,
            client=client,
        )
        db.commit()
        return result
    finally:
        client.close()
        db.close()


@router.get("/groups")
def list_groups(
    actor_user_id: Annotated[str, Depends(require_service_auth)],
) -> dict:
    """All open group sessions — public pool (§14.1)."""
    _require_wg_enabled()
    _ = actor_user_id
    factory = get_session_factory()
    db = factory()
    try:
        items = list_open_group_sessions(db)
        return {"groups": items}
    finally:
        db.close()


@router.get("/groups/{session_id}/thread")
def get_group_thread(
    session_id: str,
    actor_user_id: Annotated[str, Depends(require_service_auth)],
) -> dict:
    """Group message thread + pending draft (§14)."""
    _require_wg_enabled()
    _ = actor_user_id
    factory = get_session_factory()
    db = factory()
    try:
        session = db.get(WgSession, session_id)
        if session is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="session_not_found",
            )
        return get_wg_thread_for_session(db, session)
    finally:
        db.close()


@router.post("/wg/drafts/{draft_id}/send")
def post_wg_draft_send(
    draft_id: str,
    body: SendDraftBody,
    actor_user_id: Annotated[str, Depends(require_service_auth)],
) -> dict:
    _require_wg_enabled()
    factory = get_session_factory()
    db = factory()
    client = _aibot_client()
    try:
        result = send_wg_draft_as_agent(
            db,
            draft_id=draft_id,
            actor=actor_user_id,
            client=client,
            expected_version=body.expected_version,
        )
        db.commit()
        return result
    finally:
        client.close()
        db.close()


@router.post("/wg/drafts/{draft_id}/send-edited")
def post_wg_draft_send_edited(
    draft_id: str,
    body: SendEditedBody,
    actor_user_id: Annotated[str, Depends(require_service_auth)],
) -> dict:
    _require_wg_enabled()
    factory = get_session_factory()
    db = factory()
    client = _aibot_client()
    try:
        result = send_wg_draft_edited(
            db,
            draft_id=draft_id,
            actor=actor_user_id,
            text=body.text,
            client=client,
            expected_version=body.expected_version,
        )
        db.commit()
        return result
    finally:
        client.close()
        db.close()


@router.post("/groups/{session_id}/send-manual")
def post_wg_send_manual(
    session_id: str,
    body: SendManualBody,
    actor_user_id: Annotated[str, Depends(require_service_auth)],
) -> dict:
    _require_wg_enabled()
    factory = get_session_factory()
    db = factory()
    client = _aibot_client()
    try:
        result = send_wg_manual(
            db,
            session_id=session_id,
            actor=actor_user_id,
            text=body.text,
            client=client,
        )
        db.commit()
        return result
    finally:
        client.close()
        db.close()
