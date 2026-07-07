"""WeCom group ingress filtering (§12 · CS-40)."""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


def is_non_text_ingress(payload: dict[str, Any]) -> bool:
    """True when payload should be ignored (non-text · CS-40)."""
    msgtype = str(payload.get("msgtype") or payload.get("msg_type") or "").strip().lower()
    if msgtype and msgtype != "text":
        return True
    text = payload.get("text")
    if isinstance(text, dict):
        content = str(text.get("content") or "").strip()
    else:
        content = str(text or "").strip()
    return not content


def log_non_text_ignored(*, chatid: str, msgid: str, msgtype: str | None) -> None:
    logger.debug(
        "wg ingress ignored non-text chatid=%s msgid=%s msgtype=%s",
        chatid,
        msgid,
        msgtype or "unknown",
    )
