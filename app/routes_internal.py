"""Internal routes — service token only (M7 servicer admin)."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.api.deps import require_service_auth, verify_service_token
from app.db import get_session_factory
from app.services.servicer_admin import (
    ServicerInput,
    is_user_participant,
    list_kf_accounts,
    list_servicers_for_kf,
    replace_servicers,
)
from app.services.wecom_kf_client import WecomKfClient

router = APIRouter(prefix="/cservice/_internal", tags=["cservice-internal"])


class ServicerItemIn(BaseModel):
    user_id: str
    sort_order: int = 0
    servicer_userid: str


class PutServicersBody(BaseModel):
    servicers: list[ServicerItemIn] = Field(default_factory=list)


@router.get("/auth-check")
def auth_check(
    actor_user_id: Annotated[str, Depends(require_service_auth)],
) -> dict[str, Any]:
    return {"ok": True, "actor": actor_user_id}


@router.get("/users/{user_id}/is-participant")
def get_is_participant(
    user_id: str,
    _: Annotated[None, Depends(verify_service_token)],
) -> dict[str, bool]:
    factory = get_session_factory()
    db = factory()
    try:
        return {"is_participant": is_user_participant(db, user_id)}
    finally:
        db.close()


@router.get("/kf/accounts")
def get_kf_accounts(
    _: Annotated[None, Depends(verify_service_token)],
) -> dict[str, Any]:
    factory = get_session_factory()
    db = factory()
    try:
        return {"accounts": list_kf_accounts(db)}
    finally:
        db.close()


@router.get("/kf/{open_kfid}/servicers")
def get_kf_servicers(
    open_kfid: str,
    _: Annotated[None, Depends(verify_service_token)],
) -> dict[str, Any]:
    factory = get_session_factory()
    db = factory()
    try:
        rows = list_servicers_for_kf(db, open_kfid)
        return {
            "open_kfid": open_kfid,
            "servicers": [
                {
                    "user_id": row.user_id,
                    "sort_order": row.sort_order,
                    "servicer_userid": row.servicer_userid,
                    "enabled": row.enabled,
                }
                for row in rows
            ],
        }
    finally:
        db.close()


@router.put("/kf/{open_kfid}/servicers")
def put_kf_servicers(
    open_kfid: str,
    body: PutServicersBody,
    _: Annotated[None, Depends(verify_service_token)],
) -> dict[str, Any]:
    factory = get_session_factory()
    db = factory()
    try:
        inputs = [
            ServicerInput(
                user_id=item.user_id.strip(),
                sort_order=item.sort_order,
                servicer_userid=item.servicer_userid.strip(),
            )
            for item in body.servicers
            if item.user_id.strip() and item.servicer_userid.strip()
        ]
        with WecomKfClient() as client:
            results = replace_servicers(db, open_kfid, inputs, client)
        return {
            "open_kfid": open_kfid,
            "saved": True,
            "result_list": [
                {
                    "user_id": r.user_id,
                    "servicer_userid": r.servicer_userid,
                    "action": r.action,
                    "errcode": r.errcode,
                    "errmsg": r.errmsg,
                }
                for r in results
            ],
        }
    except ValueError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
