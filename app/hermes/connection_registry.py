"""Hermes Gateway connection registry (M3)."""

from __future__ import annotations

import json
import logging
import queue
from dataclasses import dataclass
from typing import Any

from fastapi import WebSocket

logger = logging.getLogger(__name__)


@dataclass
class RegisteredGateway:
    ws: WebSocket
    gateway_role: str = "cservice"
    agent_slug: str = ""


_gateway: RegisteredGateway | None = None
_outbound: queue.Queue[dict[str, Any]] = queue.Queue()


def reset_registry() -> None:
    global _gateway
    _gateway = None
    while not _outbound.empty():
        try:
            _outbound.get_nowait()
        except queue.Empty:
            break


def is_cservice_gateway_registered() -> bool:
    return _gateway is not None and _gateway.gateway_role == "cservice"


def get_gateway() -> RegisteredGateway | None:
    return _gateway


def apply_gateway_register(ws: WebSocket, *, agent_slug: str) -> None:
    global _gateway
    _gateway = RegisteredGateway(ws=ws, agent_slug=agent_slug)
    logger.info("cservice gateway registered slug=%s", agent_slug)


def unregister(ws: WebSocket) -> None:
    global _gateway
    if _gateway is not None and _gateway.ws is ws:
        _gateway = None
        logger.info("cservice gateway unregistered")


def queue_outbound(payload: dict[str, Any]) -> bool:
    """Thread-safe enqueue for sync pipeline callers."""
    if not is_cservice_gateway_registered():
        return False
    _outbound.put(payload)
    return True


async def drain_outbound() -> int:
    """Flush queued uplink frames to Gateway."""
    gw = _gateway
    if gw is None:
        return 0
    sent = 0
    while True:
        try:
            payload = _outbound.get_nowait()
        except queue.Empty:
            break
        try:
            await gw.ws.send_text(json.dumps(payload))
            sent += 1
        except Exception:
            logger.warning("failed to send to gateway", exc_info=True)
            unregister(gw.ws)
            break
    return sent


async def send_to_gateway(payload: dict[str, Any]) -> bool:
    """Send JSON frame immediately to registered Gateway."""
    gw = _gateway
    if gw is None:
        return False
    try:
        await gw.ws.send_text(json.dumps(payload))
        return True
    except Exception:
        logger.warning("failed to send to gateway", exc_info=True)
        unregister(gw.ws)
        return False
