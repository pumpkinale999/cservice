"""WeCom kf callback crypto (§20 · WXBizMsgCrypt compatible)."""

from __future__ import annotations

import base64
import hashlib
import socket
import struct
import xml.etree.ElementTree as ET
from typing import Any

from Crypto.Cipher import AES

from app.services.wecom_errors import CserviceWecomError


class WecomKfCryptError(CserviceWecomError):
    pass


def _sha1_signature(*parts: str) -> str:
    items = sorted(str(p) for p in parts)
    return hashlib.sha1("".join(items).encode("utf-8")).hexdigest()


def _decode_aes_key(encoding_aes_key: str) -> bytes:
    key = encoding_aes_key.strip()
    if len(key) != 43:
        raise WecomKfCryptError(-40004, "invalid aes key length")
    return base64.b64decode(key + "=")


def _pkcs7_pad(data: bytes, block_size: int = 32) -> bytes:
    pad = block_size - (len(data) % block_size)
    return data + bytes([pad]) * pad


def _pkcs7_unpad(data: bytes) -> bytes:
    if not data:
        raise WecomKfCryptError(-40007, "invalid padding")
    pad = data[-1]
    if pad < 1 or pad > 32:
        raise WecomKfCryptError(-40007, "invalid padding")
    return data[:-pad]


class WecomKfCrypt:
    def __init__(self, token: str, encoding_aes_key: str, corp_id: str) -> None:
        self.token = token
        self.corp_id = corp_id
        self.aes_key = _decode_aes_key(encoding_aes_key)

    def verify_signature(
        self,
        msg_signature: str,
        timestamp: str,
        nonce: str,
        encrypted: str,
    ) -> None:
        expected = _sha1_signature(self.token, timestamp, nonce, encrypted)
        if expected != msg_signature:
            raise WecomKfCryptError(-40001, "signature mismatch")

    def decrypt(self, encrypted: str) -> str:
        cipher = AES.new(self.aes_key, AES.MODE_CBC, self.aes_key[:16])
        plain_padded = cipher.decrypt(base64.b64decode(encrypted))
        plain = _pkcs7_unpad(plain_padded)
        msg_len = socket.ntohl(struct.unpack("I", plain[16:20])[0])
        msg = plain[20 : 20 + msg_len].decode("utf-8")
        from_corp = plain[20 + msg_len :].decode("utf-8")
        if from_corp != self.corp_id:
            raise WecomKfCryptError(-40005, "corp_id mismatch")
        return msg

    def encrypt(self, plain: str) -> str:
        msg_bytes = plain.encode("utf-8")
        corp_bytes = self.corp_id.encode("utf-8")
        rand = hashlib.sha256(plain.encode()).digest()[:16]
        body = rand + struct.pack("I", socket.htonl(len(msg_bytes))) + msg_bytes + corp_bytes
        padded = _pkcs7_pad(body)
        cipher = AES.new(self.aes_key, AES.MODE_CBC, self.aes_key[:16])
        return base64.b64encode(cipher.encrypt(padded)).decode("utf-8")

    def verify_url(
        self,
        msg_signature: str,
        timestamp: str,
        nonce: str,
        echostr: str,
    ) -> str:
        self.verify_signature(msg_signature, timestamp, nonce, echostr)
        return self.decrypt(echostr)

    def decrypt_post(
        self,
        msg_signature: str,
        timestamp: str,
        nonce: str,
        post_body: str,
    ) -> str:
        root = ET.fromstring(post_body)
        encrypt_node = root.find("Encrypt")
        if encrypt_node is None or not encrypt_node.text:
            raise WecomKfCryptError(-40002, "missing Encrypt")
        encrypted = encrypt_node.text
        self.verify_signature(msg_signature, timestamp, nonce, encrypted)
        return self.decrypt(encrypted)


def parse_kf_event_xml(plain_xml: str) -> dict[str, Any]:
    root = ET.fromstring(plain_xml)
    return {child.tag: (child.text or "") for child in root}
