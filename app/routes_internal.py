"""Internal dev/test routes (M1 auth smoke)."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.deps import require_service_auth

router = APIRouter(prefix="/cservice/_internal", tags=["cservice-internal"])


@router.get("/auth-check")
def auth_check(actor_user_id: Annotated[str, Depends(require_service_auth)]) -> dict:
    return {"ok": True, "actor": actor_user_id}
