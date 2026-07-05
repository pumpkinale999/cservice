"""Hermes WSS endpoint (M3)."""

from __future__ import annotations

import asyncio
import json
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.config import get_settings
from app.db import get_session_factory
from app.hermes import connection_registry
from app.hermes.deps import verify_adapter_bearer
from app.hermes.downlink_handler import apply_draft_downlink
from app.hermes.schemas import GatewayRegister, parse_business_frame
from app.hermes.uplink_queue import flush_pending_uplinks

logger = logging.getLogger(__name__)

router = APIRouter(tags=["hermes"])


async def _outbound_pump(stop: asyncio.Event) -> None:
    while not stop.is_set():
        await connection_registry.drain_outbound()
        try:
            await asyncio.wait_for(stop.wait(), timeout=0.05)
            return
        except TimeoutError:
            pass


@router.websocket("/hermes")
async def cservice_hermes_websocket(ws: WebSocket) -> None:
    if not verify_adapter_bearer(ws):
        await ws.close(code=4401)
        return

    await ws.accept()
    stop = asyncio.Event()
    pump = asyncio.create_task(_outbound_pump(stop))
    try:
        while True:
            raw = await ws.receive_text()
            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                await ws.send_text(json.dumps({"type": "error", "detail": "invalid json"}))
                continue

            if not isinstance(data, dict):
                await ws.send_text(json.dumps({"type": "error", "detail": "invalid frame"}))
                continue

            if data.get("type") == "ping":
                await ws.send_text(json.dumps({"type": "pong", "t": data.get("t")}))
                continue

            reg = GatewayRegister.from_dict(data)
            if reg is not None:
                connection_registry.apply_gateway_register(ws, agent_slug=reg.agent_slug)
                await ws.send_text(json.dumps({"type": "gateway_register_ok"}))
                factory = get_session_factory()
                db = factory()
                try:
                    await flush_pending_uplinks(db, force_all=True)
                    db.commit()
                finally:
                    db.close()
                await connection_registry.drain_outbound()
                continue

            reply = parse_business_frame(data)
            if reply is not None:
                factory = get_session_factory()
                db = factory()
                try:
                    ok = apply_draft_downlink(db, reply)
                    await ws.send_text(
                        json.dumps({"type": "cservice_draft_reply_ok", "accepted": ok})
                    )
                finally:
                    db.close()
                await connection_registry.drain_outbound()
                continue

            await ws.send_text(json.dumps({"type": "error", "detail": "unknown type"}))
            await connection_registry.drain_outbound()
    except WebSocketDisconnect:
        pass
    finally:
        stop.set()
        pump.cancel()
        try:
            await pump
        except asyncio.CancelledError:
            pass
        connection_registry.unregister(ws)
