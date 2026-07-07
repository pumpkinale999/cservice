"""WeCom group display_name enrichment (§9.4 · P4+)."""

from __future__ import annotations

import logging
import re
from typing import Any

from sqlalchemy.orm import Session

from app.models import WgGroup
from app.services.wecom_errors import CserviceWecomError
from app.services.wecom_kf_client import WecomKfClient

logger = logging.getLogger(__name__)

_PLACEHOLDER_RE = re.compile(r"^群·")


def display_name_is_placeholder(group: WgGroup) -> bool:
    name = (group.display_name or "").strip()
    if not name:
        return True
    return bool(_PLACEHOLDER_RE.match(name))


def _name_from_payload(payload: dict[str, Any]) -> str:
    direct = str(payload.get("group_display_name") or "").strip()
    if direct:
        return direct
    raw = payload.get("raw")
    if not isinstance(raw, dict):
        return ""
    body = raw.get("body")
    if not isinstance(body, dict):
        return ""
    for key in ("chatname", "roomname", "group_name", "name"):
        val = str(body.get(key) or "").strip()
        if val:
            return val
    return ""


def fetch_groupchat_name(client: WecomKfClient, chatid: str) -> str | None:
    """Resolve group name via externalcontact/groupchat/get."""
    cid = (chatid or "").strip()
    if not cid:
        return None
    data = client.groupchat_get(cid)
    group_chat = data.get("group_chat")
    if not isinstance(group_chat, dict):
        return None
    name = str(group_chat.get("name") or "").strip()
    return name or None


def refresh_group_display_name(
    group: WgGroup,
    payload: dict[str, Any] | None = None,
    *,
    client: WecomKfClient | None = None,
) -> bool:
    """Update stored display_name from ingress payload or WeCom API."""
    payload = payload or {}
    explicit = _name_from_payload(payload)
    if explicit and explicit != group.display_name:
        group.display_name = explicit
        return True

    if client is None:
        return False

    try:
        remote = fetch_groupchat_name(client, group.chatid)
    except CserviceWecomError as exc:
        logger.debug(
            "groupchat_get failed chatid=%s errcode=%s",
            group.chatid,
            exc.errcode,
        )
        return False

    if remote and remote != group.display_name:
        group.display_name = remote
        return True
    return False


def enrich_group_display_names(
    db: Session,
    client: WecomKfClient,
    groups: list[WgGroup],
) -> None:
    """Refresh placeholder group names before list/thread render."""
    pending = [g for g in groups if display_name_is_placeholder(g)]
    if not pending:
        return
    for group in pending:
        refresh_group_display_name(group, client=client)
