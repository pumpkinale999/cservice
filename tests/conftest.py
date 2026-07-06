"""Shared pytest fixtures for M2."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import httpx
import pytest
from alembic import command
from alembic.config import Config

from app.config import get_settings
from app.db import get_session_factory, reset_engine_cache
from app.services.seed import load_seed_file
from app.services.sync_job import set_client_factory, set_sync_runner
from app.services.uplink_hook import NoopUplinkHook
from app.services.wecom_kf_client import WecomKfClient, reset_token_cache
from app.services.wecom_kf_crypto import WecomKfCrypt

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "cservice"

TEST_TOKEN = "test_callback_token"
TEST_AES_KEY = "MDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDA"
TEST_CORP_ID = "wwTESTcorp"


@pytest.fixture()
def tmp_cservice_db(tmp_path, monkeypatch):
    db_path = tmp_path / "cservice.db"
    monkeypatch.setenv("CSERVICE_DB_PATH", str(db_path))
    get_settings.cache_clear()
    reset_engine_cache()
    repo_root = Path(__file__).resolve().parents[1]
    cfg = Config(str(repo_root / "alembic.ini"))
    cfg.set_main_option("sqlalchemy.url", f"sqlite:///{db_path}")
    cfg.attributes["skip_log_config"] = True
    command.upgrade(cfg, "head")
    yield db_path
    reset_engine_cache()


@pytest.fixture
def wecom_env(monkeypatch):
    monkeypatch.setenv("CSERVICE_WECOM_CORP_ID", TEST_CORP_ID)
    monkeypatch.setenv("CSERVICE_WECOM_SECRET", "test_secret")
    monkeypatch.setenv("CSERVICE_KF_CALLBACK_TOKEN", TEST_TOKEN)
    monkeypatch.setenv("CSERVICE_KF_CALLBACK_AES_KEY", TEST_AES_KEY)
    get_settings.cache_clear()
    reset_token_cache()
    yield
    reset_token_cache()
    get_settings.cache_clear()


@pytest.fixture
def wecom_crypt(wecom_env):
    return WecomKfCrypt(TEST_TOKEN, TEST_AES_KEY, TEST_CORP_ID)


@pytest.fixture
def loaded_seed(tmp_cservice_db):
    factory = get_session_factory()
    session = factory()
    try:
        load_seed_file(FIXTURES / "seed_minimal.yaml", session)
    finally:
        session.close()
    return tmp_cservice_db


def load_json_fixture(name: str) -> dict[str, Any]:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def build_mock_wecom_client(
    *,
    sync_responses: list[dict[str, Any]] | None = None,
    trans_ok: bool = True,
    get_ok: bool = True,
    customer_batchget_response: dict[str, Any] | None = None,
) -> MagicMock:
    client = MagicMock(spec=WecomKfClient)
    sync_responses = sync_responses or [load_json_fixture("sync_msg_text_inbound.json")]
    client.sync_msg.side_effect = sync_responses
    if get_ok:
        client.service_state_get.return_value = load_json_fixture(
            "service_state_get_ok.json"
        )
    else:
        from app.services.wecom_errors import CserviceWecomError

        client.service_state_get.side_effect = CserviceWecomError(95014, "fail")
    if trans_ok:
        client.service_state_trans.return_value = load_json_fixture(
            "service_state_trans_ok.json"
        )
    else:
        from app.services.wecom_errors import CserviceWecomError

        client.service_state_trans.side_effect = CserviceWecomError(95014, "fail")
    batchget_fixture = customer_batchget_response or load_json_fixture(
        "customer_batchget_ok.json"
    )

    def _customer_batchget(external_userid_list: list[str], **kwargs: Any) -> dict[str, Any]:
        by_id = {
            row["external_userid"]: row
            for row in batchget_fixture.get("customer_list") or []
        }
        customer_list = [
            by_id[uid]
            for uid in external_userid_list
            if uid in by_id
        ]
        invalid = [
            uid
            for uid in external_userid_list
            if uid not in by_id
        ]
        return {
            "errcode": 0,
            "errmsg": "ok",
            "customer_list": customer_list,
            "invalid_external_userid": invalid,
        }

    client.customer_batchget.side_effect = _customer_batchget
    client.send_text_msg = MagicMock()
    return client


@pytest.fixture
def mock_wecom_client():
    return build_mock_wecom_client()


@pytest.fixture(autouse=True)
def reset_sync_hooks():
    from app.hermes import connection_registry

    set_sync_runner(None)
    set_client_factory(None)
    connection_registry.reset_registry()
    yield
    set_sync_runner(None)
    set_client_factory(None)
    connection_registry.reset_registry()


@pytest.fixture
def noop_uplink_hook():
    return NoopUplinkHook()


def mock_token_transport() -> httpx.MockTransport:
    def handler(request: httpx.Request) -> httpx.Response:
        if "/cgi-bin/gettoken" in str(request.url):
            return httpx.Response(
                200,
                json={"errcode": 0, "errmsg": "ok", "access_token": "AT123", "expires_in": 7200},
            )
        return httpx.Response(404, json={"errcode": 404})

    return httpx.MockTransport(handler)
