"""WeCom group internal ingress tests (CS-29 · CS-41)."""

from __future__ import annotations

from fastapi.testclient import TestClient
from unittest.mock import patch

from app.config import get_settings
from app.db import get_session_factory
from app.main import app
from app.models import WgGroup, WgMessage, WgReplyAnchor
from app.services.wg_group_query import list_open_group_sessions
from tests.conftest import load_json_fixture

TOKEN = "test-service-token"
HEADERS = {"Authorization": f"Bearer {TOKEN}"}
INGRESS_URL = "/api/v1/cservice/_internal/wecom-group/ingress"


def _enable_wg(monkeypatch) -> None:
    monkeypatch.setenv("CSERVICE_SERVICE_TOKEN", TOKEN)
    monkeypatch.setenv("CSERVICE_WG_ENABLED", "1")
    get_settings.cache_clear()


def test_ingress_happy_path_cs29(tmp_cservice_db, monkeypatch):
    _enable_wg(monkeypatch)
    payload = load_json_fixture("wg_ingress_text.json")
    client = TestClient(app)

    r = client.post(INGRESS_URL, json=payload, headers=HEADERS)
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is True
    assert body["auto_registered"] is True
    assert body["pending_reply_count"] == 1
    assert body["group_display_name"] == "测试健康群"

    factory = get_session_factory()
    db = factory()
    try:
        group = db.get(WgGroup, payload["chatid"])
        assert group is not None
        msg = db.query(WgMessage).filter_by(source_msgid=payload["msgid"]).one()
        assert msg.direction == "inbound"
        assert msg.content == payload["text"]
        anchor = db.get(WgReplyAnchor, payload["chatid"])
        assert anchor is not None
        assert anchor.response_url == payload["response_url"]
        assert anchor.source_msgid == payload["msgid"]
    finally:
        db.close()


def test_ingress_auto_register_list_visible_cs41(tmp_cservice_db, monkeypatch):
    _enable_wg(monkeypatch)
    payload = load_json_fixture("wg_ingress_text.json")
    payload["chatid"] = "wrNEWGROUP99"
    payload["msgid"] = "msg_wg_new_99"
    payload.pop("group_display_name", None)

    client = TestClient(app)
    with patch(
        "app.services.wg_group_display.fetch_groupchat_name",
        return_value="自动同步群名",
    ):
        r = client.post(INGRESS_URL, json=payload, headers=HEADERS)
    assert r.status_code == 200
    assert r.json()["auto_registered"] is True
    assert r.json()["group_display_name"] == "自动同步群名"

    factory = get_session_factory()
    db = factory()
    try:
        rows = list_open_group_sessions(db)
        chatids = {row["chatid"] for row in rows}
        assert "wrNEWGROUP99" in chatids
        row = next(r for r in rows if r["chatid"] == "wrNEWGROUP99")
        assert row["group_display_name"] == "自动同步群名"
        assert row["pending_reply_count"] == 1
    finally:
        db.close()


def test_ingress_dedup(tmp_cservice_db, monkeypatch):
    _enable_wg(monkeypatch)
    payload = load_json_fixture("wg_ingress_text.json")
    client = TestClient(app)

    r1 = client.post(INGRESS_URL, json=payload, headers=HEADERS)
    r2 = client.post(INGRESS_URL, json=payload, headers=HEADERS)
    assert r1.status_code == 200
    assert r2.status_code == 200
    assert r2.json()["duplicate"] is True

    factory = get_session_factory()
    db = factory()
    try:
        count = db.query(WgMessage).filter_by(source_msgid=payload["msgid"]).count()
        assert count == 1
    finally:
        db.close()


def test_ingress_anchor_updates_on_second_at(tmp_cservice_db, monkeypatch):
    _enable_wg(monkeypatch)
    payload = load_json_fixture("wg_ingress_text.json")
    client = TestClient(app)

    client.post(INGRESS_URL, json=payload, headers=HEADERS)

    payload2 = {**payload, "msgid": "msg_wg_002", "response_url": "https://example.com/new-url"}
    client.post(INGRESS_URL, json=payload2, headers=HEADERS)

    factory = get_session_factory()
    db = factory()
    try:
        anchor = db.get(WgReplyAnchor, payload["chatid"])
        assert anchor is not None
        assert anchor.response_url == "https://example.com/new-url"
        assert anchor.source_msgid == "msg_wg_002"
    finally:
        db.close()


def test_ingress_unknown_group_when_auto_register_off(tmp_cservice_db, monkeypatch):
    monkeypatch.setenv("CSERVICE_SERVICE_TOKEN", TOKEN)
    monkeypatch.setenv("CSERVICE_WG_ENABLED", "1")
    monkeypatch.setenv("CSERVICE_WG_AUTO_REGISTER", "0")
    get_settings.cache_clear()

    payload = load_json_fixture("wg_ingress_text.json")
    client = TestClient(app)
    r = client.post(INGRESS_URL, json=payload, headers=HEADERS)
    assert r.status_code == 403
    assert r.json()["detail"] == "unknown_group"


def test_ingress_wg_disabled_503(tmp_cservice_db, monkeypatch):
    monkeypatch.setenv("CSERVICE_SERVICE_TOKEN", TOKEN)
    monkeypatch.setenv("CSERVICE_WG_ENABLED", "0")
    get_settings.cache_clear()

    payload = load_json_fixture("wg_ingress_text.json")
    client = TestClient(app)
    r = client.post(INGRESS_URL, json=payload, headers=HEADERS)
    assert r.status_code == 503
    assert r.json()["detail"] == "wg_disabled"
