"""Group send coordinator tests."""

from __future__ import annotations

import asyncio

import pytest

from app.hermes import connection_registry
from app.hermes.group_send_coordinator import (
    request_group_send,
    reset_group_send_coordinator,
    resolve_group_send_result,
)


@pytest.mark.asyncio
async def test_request_group_send_offline():
    reset_group_send_coordinator()
    connection_registry.reset_registry()
    result = await request_group_send("wr001", "hello")
    assert result == {"ok": False, "code": "gateway_offline"}


@pytest.mark.asyncio
async def test_resolve_completes_pending():
    reset_group_send_coordinator()
    connection_registry.reset_registry()

    class FakeWs:
        sent: list[str] = []

        async def send_text(self, payload: str) -> None:
            self.sent.append(payload)

    ws = FakeWs()
    connection_registry.apply_gateway_register(ws, agent_slug="cservice-assistant", gateway_role="cservice")

    async def run_send():
        return await request_group_send("wr001", "hello", timeout=2.0)

    task = asyncio.create_task(run_send())
    await asyncio.sleep(0.05)
    # parse sent frame to get request_id
    import json

    assert len(ws.sent) == 1
    frame = json.loads(ws.sent[0])
    request_id = frame["request_id"]
    assert frame["type"] == "cservice_group_send"
    assert frame["chatid"] == "wr001"

    ok = resolve_group_send_result(
        {
            "type": "cservice_group_send_result",
            "request_id": request_id,
            "ok": True,
        }
    )
    assert ok is True
    result = await task
    assert result == {"ok": True, "code": "", "errcode": None, "errmsg": ""}
