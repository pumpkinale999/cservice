"""Webhook crypto tests (M2 · PR-1)."""

from __future__ import annotations

import hashlib

import pytest

from app.services.wecom_kf_crypto import WecomKfCrypt, WecomKfCryptError


def test_verify_url_roundtrip(wecom_crypt):
    plain = "echostr_test_value"
    encrypted = wecom_crypt.encrypt(plain)
    ts = "1710000000"
    nonce = "nonce123"
    sig = _sig(wecom_crypt.token, ts, nonce, encrypted)
    assert wecom_crypt.verify_url(sig, ts, nonce, encrypted) == plain


def test_decrypt_post_xml(wecom_crypt):
    inner = (FIXTURES / "webhook_kf_msg_or_event.xml").read_text(encoding="utf-8")
    encrypted = wecom_crypt.encrypt(inner)
    ts = "1710000001"
    nonce = "nonce456"
    sig = _sig(wecom_crypt.token, ts, nonce, encrypted)
    body = f'<xml><Encrypt><![CDATA[{encrypted}]]></Encrypt></xml>'
    plain = wecom_crypt.decrypt_post(sig, ts, nonce, body)
    assert "kf_msg_or_event" in plain


def test_bad_signature_rejected(wecom_crypt):
    encrypted = wecom_crypt.encrypt("x")
    with pytest.raises(WecomKfCryptError):
        wecom_crypt.verify_url("bad", "1", "2", encrypted)


def _sig(token: str, ts: str, nonce: str, encrypted: str) -> str:
    items = sorted([token, ts, nonce, encrypted])
    return hashlib.sha1("".join(items).encode()).hexdigest()


FIXTURES = __import__("pathlib").Path(__file__).resolve().parent / "fixtures" / "cservice"
