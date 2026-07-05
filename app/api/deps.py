"""FastAPI dependencies — service token auth (M1 · M4 BFF)."""

from __future__ import annotations

from typing import Annotated

from fastapi import Header, HTTPException, status

from app.config import get_settings


def verify_service_token(
    authorization: Annotated[str | None, Header()] = None,
) -> None:
    """Validate Bearer service token from skstudio BFF."""
    token = get_settings().cservice_service_token.strip()
    if not token:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="cservice_service_token_not_configured",
        )
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="missing_service_token",
        )
    provided = authorization.removeprefix("Bearer ").strip()
    if provided != token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid_service_token",
        )


def get_actor_user_id(
    x_skstudio_user_id: Annotated[str | None, Header(alias="X-Skstudio-User-Id")] = None,
) -> str:
    """Actor userid forwarded by skstudio BFF (wecom_userid)."""
    actor = (x_skstudio_user_id or "").strip()
    if not actor:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="missing_actor_user_id",
        )
    return actor


def require_service_auth(
    authorization: Annotated[str | None, Header()] = None,
    x_skstudio_user_id: Annotated[str | None, Header(alias="X-Skstudio-User-Id")] = None,
) -> str:
    """Combined service token + actor header check."""
    verify_service_token(authorization)
    return get_actor_user_id(x_skstudio_user_id)
