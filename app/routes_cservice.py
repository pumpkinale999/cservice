"""REST routes — cservice domain API (M1 health · M4+ customers/drafts)."""

from __future__ import annotations

from fastapi import APIRouter

from app.config import get_settings
from app.db import db_ok, table_exists

router = APIRouter(prefix="/cservice", tags=["cservice"])


@router.get("/health")
def cservice_health() -> dict:
    """M1 health probe — see skstudio docs/cservice-产品设计.md §26.4."""
    settings = get_settings()
    wecom_configured = settings.wecom_configured()
    db = db_ok() and table_exists("cservice_kf_account")
    ok = db
    return {
        "ok": ok,
        "enabled": True,
        "db": db,
        "wecom_configured": wecom_configured,
        "wecom_token": None if not wecom_configured else "not_checked_m1",
        "sync_cursor_age_seconds": None,
        "hermes_cservice_gateway": None,
        "open_kfid_count": None,
        "service": "cservice",
    }
