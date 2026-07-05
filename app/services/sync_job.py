"""Background sync job enqueue (§21.1)."""

from __future__ import annotations

import logging
from collections.abc import Callable

from app.services.sync_pipeline import run_sync_job
from app.services.wecom_kf_client import WecomKfClient

logger = logging.getLogger(__name__)

_sync_runner: Callable[[str, str | None], None] | None = None
_client_factory: Callable[[], WecomKfClient] | None = None


def set_sync_runner(runner: Callable[[str, str | None], None]) -> None:
    global _sync_runner
    _sync_runner = runner


def set_client_factory(factory: Callable[[], WecomKfClient]) -> None:
    global _client_factory
    _client_factory = factory


def _default_client() -> WecomKfClient:
    return WecomKfClient()


def enqueue_sync(open_kfid: str, token: str) -> None:
    runner = _sync_runner or _run_default_sync
    runner(open_kfid, token)


def _run_default_sync(open_kfid: str, token: str | None) -> None:
    factory = _client_factory or _default_client
    client = factory()
    try:
        run_sync_job(open_kfid, token, client)
    finally:
        client.close()


def run_sync_job_now(open_kfid: str, token: str | None, client: WecomKfClient) -> None:
    """Synchronous entry for tests."""
    run_sync_job(open_kfid, token, client)
