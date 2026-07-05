"""Webhook route tests (M2 · PR-2)."""

from __future__ import annotations

import hashlib
from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "cservice"


def _sig(token: str, ts: str, nonce: str, encrypted: str) -> str:
    return hashlib.sha1("".join(sorted([token, ts, nonce, encrypted])).encode()).hexdigest()


def test_kf_callback_get_verify(wecom_crypt, wecom_env, tmp_cservice_db):
    plain = "verify_echo"
    enc = wecom_crypt.encrypt(plain)
    ts, nonce = "1710000000", "n1"
    sig = _sig(wecom_crypt.token, ts, nonce, enc)
    client = TestClient(app)
    r = client.get(
        "/api/v1/cservice/kf/callback",
        params={"msg_signature": sig, "timestamp": ts, "nonce": nonce, "echostr": enc},
    )
    assert r.status_code == 200
    assert r.text == plain


def test_kf_callback_post_success(wecom_crypt, wecom_env, tmp_cservice_db, monkeypatch):
    enqueued = []

    def capture(open_kfid: str, token: str) -> None:
        enqueued.append((open_kfid, token))

    from app.services import kf_webhook_handler

    monkeypatch.setattr(kf_webhook_handler, "enqueue_sync", capture)

    inner = (FIXTURES / "webhook_kf_msg_or_event.xml").read_text(encoding="utf-8")
    enc = wecom_crypt.encrypt(inner)
    ts, nonce = "1710000002", "n2"
    sig = _sig(wecom_crypt.token, ts, nonce, enc)
    body = f'<xml><Encrypt><![CDATA[{enc}]]></Encrypt></xml>'
    client = TestClient(app)
    r = client.post(
        "/api/v1/cservice/kf/callback",
        params={"msg_signature": sig, "timestamp": ts, "nonce": nonce},
        content=body,
    )
    assert r.status_code == 200
    assert r.text == "success"
