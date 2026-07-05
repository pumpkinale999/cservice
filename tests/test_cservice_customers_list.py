"""GET /customers tests (M4 PR-1)."""

from __future__ import annotations

import uuid

from fastapi.testclient import TestClient

from app.config import get_settings
from app.db import get_session_factory
from app.main import app
from app.models import Customer, Message, Session as CSession

TOKEN = "test-service-token"
ZHANGSAN = "zhangsan"
LISI = "lisi"


def _auth_headers(actor: str = ZHANGSAN) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {TOKEN}",
        "X-Skstudio-User-Id": actor,
    }


def _seed_session(
    db,
    *,
    servicer: str,
    pending: int = 1,
    status: str = "open",
    preview: str = "你好，想咨询价格",
) -> str:
    cid = str(uuid.uuid4())
    db.add(
        Customer(
            id=cid,
            external_userid=f"wm_{servicer}",
            display_name="张三",
            first_scene="官网",
            last_scene="官网",
            created_at="2026-07-05T12:00:00+00:00",
        )
    )
    sid = str(uuid.uuid4())
    db.add(
        CSession(
            id=sid,
            open_kfid="wkTEST_MINIMAL",
            customer_id=cid,
            servicer_userid=servicer,
            status=status,
            pending_reply_count=pending,
            last_activity_at="2026-07-05T12:00:00+00:00",
        )
    )
    db.add(
        Message(
            id=str(uuid.uuid4()),
            session_id=sid,
            direction="inbound",
            wx_msgid=f"wx_{sid}",
            msg_type="text",
            content=preview,
            sender_type="customer",
            created_at="2026-07-05T12:00:00+00:00",
        )
    )
    db.flush()
    return sid


def test_customers_list_servicer_filter(loaded_seed, monkeypatch):
    monkeypatch.setenv("CSERVICE_SERVICE_TOKEN", TOKEN)
    get_settings.cache_clear()
    factory = get_session_factory()
    db = factory()
    try:
        zhang_sid = _seed_session(db, servicer=ZHANGSAN)
        _seed_session(db, servicer=LISI)
        db.commit()
    finally:
        db.close()

    client = TestClient(app)
    r = client.get("/api/v1/cservice/customers", headers=_auth_headers(ZHANGSAN))
    assert r.status_code == 200
    body = r.json()
    assert len(body["customers"]) == 1
    row = body["customers"][0]
    assert row["session_id"] == zhang_sid
    assert row["pending_reply_count"] == 1
    assert row["kf_account_short_name"] == "测试账号"
    assert row["scene"] == "官网"
    assert "咨询价格" in (row["last_message_preview"] or "")


def test_customers_list_excludes_closed(loaded_seed, monkeypatch):
    monkeypatch.setenv("CSERVICE_SERVICE_TOKEN", TOKEN)
    get_settings.cache_clear()
    factory = get_session_factory()
    db = factory()
    try:
        _seed_session(db, servicer=ZHANGSAN, status="closed")
        db.commit()
    finally:
        db.close()

    client = TestClient(app)
    r = client.get("/api/v1/cservice/customers", headers=_auth_headers())
    assert r.status_code == 200
    assert r.json()["customers"] == []


def test_thread_forbidden_other_servicer(loaded_seed, monkeypatch):
    monkeypatch.setenv("CSERVICE_SERVICE_TOKEN", TOKEN)
    get_settings.cache_clear()
    factory = get_session_factory()
    db = factory()
    try:
        sid = _seed_session(db, servicer=LISI)
        db.commit()
    finally:
        db.close()

    client = TestClient(app)
    r = client.get(
        f"/api/v1/cservice/customers/{sid}/thread",
        headers=_auth_headers(ZHANGSAN),
    )
    assert r.status_code == 403
