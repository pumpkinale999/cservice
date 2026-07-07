"""WeCom group draft CAS tests (CS-38)."""

from __future__ import annotations

from app.db import get_session_factory
from app.hermes.downlink_handler import apply_draft_downlink
from app.hermes.schemas import CserviceDraftReply
from app.models import WgDraft
from app.services.wg_draft_service import should_accept_wg_downlink
from tests.wg_helpers import TOKEN, seed_wg_draft, seed_wg_group_session, seed_wg_inbound


def test_wg_downlink_stale_trigger_rejected(tmp_cservice_db):
    factory = get_session_factory()
    db = factory()
    try:
        session, _group = seed_wg_group_session(db)
        seed_wg_inbound(db, session_id=session.id, source_msgid="m2", content="new")
        assert should_accept_wg_downlink(db, session.id, "m1") is False
    finally:
        db.close()


def test_wg_concurrent_send_second_gets_409(tmp_cservice_db, monkeypatch):
    monkeypatch.setenv("CSERVICE_DEMO_OUTBOUND", "1")
    monkeypatch.setenv("CSERVICE_SERVICE_TOKEN", TOKEN)
    monkeypatch.setenv("CSERVICE_WG_ENABLED", "1")
    from app.config import get_settings

    get_settings.cache_clear()
    from fastapi.testclient import TestClient

    from app.main import app
    from tests.wg_helpers import HEADERS, seed_wg_anchor

    factory = get_session_factory()
    db = factory()
    try:
        session, group = seed_wg_group_session(db, pending_reply_count=1)
        seed_wg_anchor(db, chatid=group.chatid)
        draft = seed_wg_draft(db, session_id=session.id, version=1)
        db.commit()
        draft_id = draft.id
    finally:
        db.close()

    client = TestClient(app)
    body = {"expected_version": 1}
    r1 = client.post(
        f"/api/v1/cservice/wg/drafts/{draft_id}/send",
        headers=HEADERS,
        json=body,
    )
    r2 = client.post(
        f"/api/v1/cservice/wg/drafts/{draft_id}/send",
        headers=HEADERS,
        json=body,
    )
    assert r1.status_code == 200
    assert r2.status_code == 409
    assert r2.json()["detail"]["code"] == "draft_concurrent_conflict"


def test_wg_superseded_draft_rejected(tmp_cservice_db, monkeypatch):
    monkeypatch.setenv("CSERVICE_DEMO_OUTBOUND", "1")
    monkeypatch.setenv("CSERVICE_SERVICE_TOKEN", "test-service-token")
    monkeypatch.setenv("CSERVICE_WG_ENABLED", "1")
    from app.config import get_settings

    get_settings.cache_clear()
    from fastapi.testclient import TestClient

    from app.main import app
    from tests.wg_helpers import HEADERS, seed_wg_anchor

    factory = get_session_factory()
    db = factory()
    try:
        session, group = seed_wg_group_session(db, pending_reply_count=1)
        seed_wg_anchor(db, chatid=group.chatid)
        draft = seed_wg_draft(db, session_id=session.id, version=1)
        draft.status = "superseded"
        db.commit()
        draft_id = draft.id
    finally:
        db.close()

    client = TestClient(app)
    r = client.post(
        f"/api/v1/cservice/wg/drafts/{draft_id}/send",
        headers=HEADERS,
        json={"expected_version": 1},
    )
    assert r.status_code == 409
    assert r.json()["detail"]["code"] == "draft_superseded"
