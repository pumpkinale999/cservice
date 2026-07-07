"""Hermes Gateway connection registry (M3 · P4-M2 multi-role)."""

from __future__ import annotations

import json
import logging
import queue
from dataclasses import dataclass
from typing import Any

from fastapi import WebSocket

logger = logging.getLogger(__name__)

KF_ROLE = "cservice"
GROUP_ROLE = "cservice-group"


@dataclass
class RegisteredGateway:
    ws: WebSocket
    gateway_role: str = KF_ROLE
    agent_slug: str = ""


_gateways: dict[str, RegisteredGateway] = {}
_outbound: dict[str, queue.Queue[dict[str, Any]]] = {
    KF_ROLE: queue.Queue(),
    GROUP_ROLE: queue.Queue(),
}


def reset_registry() -> None:
    global _gateways
    _gateways = {}
    for q in _outbound.values():
        while not q.empty():
            try:
                q.get_nowait()
            except queue.Empty:
                break


def is_cservice_gateway_registered() -> bool:
    return KF_ROLE in _gateways


def is_cservice_group_gateway_registered() -> bool:
    return GROUP_ROLE in _gateways


def get_gateway(gateway_role: str = KF_ROLE) -> RegisteredGateway | None:
    return _gateways.get(gateway_role)


def apply_gateway_register(
    ws: WebSocket,
    *,
    agent_slug: str,
    gateway_role: str = KF_ROLE,
) -> None:
    _gateways[gateway_role] = RegisteredGateway(
        ws=ws,
        gateway_role=gateway_role,
        agent_slug=agent_slug,
    )
    logger.info(
        "cservice gateway registered role=%s slug=%s",
        gateway_role,
        agent_slug,
    )


def unregister(ws: WebSocket) -> None:
    to_remove = [role for role, gw in _gateways.items() if gw.ws is ws]
    for role in to_remove:
        _gateways.pop(role, None)
        logger.info("cservice gateway unregistered role=%s", role)


def _role_for_payload(payload: dict[str, Any]) -> str:
    if payload.get("type") == "cservice_group_uplink":
        return GROUP_ROLE
    return KF_ROLE


def queue_outbound(payload: dict[str, Any], *, gateway_role: str | None = None) -> bool:
    """Thread-safe enqueue for sync pipeline callers."""
    role = gateway_role or _role_for_payload(payload)
    if role not in _gateways:
        return False
    _outbound[role].put(payload)
    return True


async def _drain_role(role: str) -> int:
    gw = _gateways.get(role)
    if gw is None:
        return 0
    q = _outbound[role]
    sent = 0
    while True:
        try:
            payload = q.get_nowait()
        except queue.Empty:
            break
        try:
            await gw.ws.send_text(json.dumps(payload))
            sent += 1
        except Exception:
            logger.warning("failed to send to gateway role=%s", role, exc_info=True)
            unregister(gw.ws)
            break
    return sent


async def drain_outbound(gateway_role: str | None = None) -> int:
    """Flush queued uplink frames to Gateway(s)."""
    if gateway_role is not None:
        return await _drain_role(gateway_role)
    total = 0
    for role in list(_gateways.keys()):
        total += await _drain_role(role)
    return total


async def send_to_gateway(payload: dict[str, Any], *, gateway_role: str | None = None) -> bool:
    """Send JSON frame immediately to registered Gateway."""
    role = gateway_role or _role_for_payload(payload)
    gw = _gateways.get(role)
    if gw is None:
        return False
    try:
        await gw.ws.send_text(json.dumps(payload))
        return True
    except Exception:
        logger.warning("failed to send to gateway role=%s", role, exc_info=True)
        unregister(gw.ws)
        return False
