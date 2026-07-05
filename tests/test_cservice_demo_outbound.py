"""Demo outbound when WeCom is not configured."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.config import get_settings
from app.db import get_session_factory
from app.main import app
from tests.cservice_send_helpers import ZHANGSAN, seed_session_with_draft

TOKEN = "test-service-token"


def test_send_draft_demo_outbound_without_wecom(loaded_seed, monkeypatch):
    monkeypatch.setenv("CSERVICE_SERVICE_TOKEN", TOKEN)
    monkeypatch.setenv("CSERVICE_DEMO_OUTBOUND", "1")
    monkeypatch.setenv("CSERVICE_WECOM_CORP_ID", "")
    monkeypatch.setenv("CSERVICE_WECOM_SECRET", "")
    get_settings.cache_clear()
    factory = get_session_factory()
    db = factory()
    try:
        _sid, draft_id = seed_session_with_draft(db)
        db.commit()
    finally:
        db.close()

    client = TestClient(app)
    r = client.post(
        f"/api/v1/cservice/drafts/{draft_id}/send",
        headers={
            "Authorization": f"Bearer {TOKEN}",
            "X-Skstudio-User-Id": ZHANGSAN,
        },
    )

    assert r.status_code == 200
    assert r.json()["delivery_status"] == "sent"
    assert str(r.json()["wx_msgid"]).startswith("demo-")
