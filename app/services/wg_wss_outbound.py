"""群主动发送传输层：经 ingress GW 企微 WSS 出站（§9.3 · P4+）。

供 manual / cron / alert 等 trigger 共用；UI「人工直发」是 trigger=manual 的一种。
"""

from __future__ import annotations

import asyncio

from app.config import Settings, get_settings
from app.hermes.group_send_coordinator import request_group_send
from app.services.wecom_error_detail import raise_for_group_send_result


def send_group_via_wss(chatid: str, content: str, *, settings: Settings | None = None) -> None:
    """Send markdown to a WeCom group through cservice-assistant ingress GW."""
    cfg = settings or get_settings()
    if cfg.cservice_demo_outbound:
        return

    result = asyncio.run(request_group_send(chatid, content))
    raise_for_group_send_result(result)
