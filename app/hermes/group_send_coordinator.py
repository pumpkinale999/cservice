"""群主动发送协调：cservice ↔ ingress GW 的 request/reply（P4+）。"""

from __future__ import annotations

import asyncio
import logging
import uuid
from typing import Any

from app.hermes import connection_registry
from app.hermes.schemas import CserviceGroupSend, CserviceGroupSendResult

logger = logging.getLogger(__name__)

_pending: dict[str, asyncio.Future[dict[str, Any]]] = {}


def reset_group_send_coordinator() -> None:
    for fut in _pending.values():
        if not fut.done():
            fut.cancel()
    _pending.clear()


def resolve_group_send_result(data: dict[str, Any]) -> bool:
    """Complete a pending send future from a gateway result frame."""
    parsed = CserviceGroupSendResult.from_dict(data)
    if parsed is None:
        return False
    fut = _pending.get(parsed.request_id)
    if fut is None or fut.done():
        return False
    fut.set_result(
        {
            "ok": parsed.ok,
            "code": parsed.code,
            "errcode": parsed.errcode,
            "errmsg": parsed.errmsg,
        }
    )
    return True


async def request_group_send(
    chatid: str,
    content: str,
    *,
    timeout: float = 15.0,
) -> dict[str, Any]:
    """向 ingress GW 发 ``cservice_group_send`` 并等待 ``cservice_group_send_result``。"""
    if not connection_registry.is_cservice_gateway_registered():
        return {"ok": False, "code": "gateway_offline"}

    request_id = uuid.uuid4().hex
    frame = CserviceGroupSend(request_id=request_id, chatid=chatid, content=content).to_dict()

    loop = asyncio.get_running_loop()
    fut: asyncio.Future[dict[str, Any]] = loop.create_future()
    _pending[request_id] = fut

    sent = await connection_registry.send_to_gateway(
        frame,
        gateway_role=connection_registry.KF_ROLE,
    )
    if not sent:
        _pending.pop(request_id, None)
        return {"ok": False, "code": "gateway_offline"}

    try:
        return await asyncio.wait_for(fut, timeout=timeout)
    except TimeoutError:
        logger.warning("proactive group send timeout chatid=%s request_id=%s", chatid, request_id)
        return {"ok": False, "code": "send_timeout"}
    finally:
        _pending.pop(request_id, None)
