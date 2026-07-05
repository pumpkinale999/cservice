"""WebSocket auth for Hermes adapter."""

from __future__ import annotations

import secrets

from fastapi import WebSocket

from app.config import get_settings


def verify_adapter_bearer(ws: WebSocket) -> bool:
    expected = get_settings().cservice_service_token.strip()
    if not expected:
        return False
    auth = ws.headers.get("authorization") or ws.headers.get("Authorization") or ""
    if not auth.lower().startswith("bearer "):
        return False
    token = auth[7:].strip()
    if not token:
        return False
    return secrets.compare_digest(token, expected)
