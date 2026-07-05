"""WeCom HTTP client tests (M2 · PR-1)."""

from __future__ import annotations

import httpx
import pytest

from app.config import get_settings
from app.services.wecom_errors import CserviceWecomError
from app.services.wecom_kf_client import WecomKfClient, reset_token_cache
from tests.conftest import load_json_fixture, mock_token_transport


def test_get_access_token_cached(wecom_env):
    reset_token_cache()
    transport = mock_token_transport()
    with WecomKfClient(http_client=httpx.Client(transport=transport)) as client:
        t1 = client.get_access_token()
        t2 = client.get_access_token()
        assert t1 == "AT123"
        assert t2 == "AT123"


def test_get_access_token_failure(wecom_env):
    reset_token_cache()

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"errcode": 40013, "errmsg": "invalid corpid"})

    with WecomKfClient(http_client=httpx.Client(transport=httpx.MockTransport(handler))) as client:
        with pytest.raises(CserviceWecomError) as exc:
            client.get_access_token(force_refresh=True)
        assert exc.value.errcode == 40013


def test_sync_msg_request_shape(wecom_env):
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        if "/gettoken" in str(request.url):
            return httpx.Response(
                200,
                json={"errcode": 0, "access_token": "AT", "expires_in": 7200},
            )
        captured["path"] = request.url.path
        captured["body"] = __import__("json").loads(request.content)
        return httpx.Response(200, json=load_json_fixture("sync_msg_text_inbound.json"))

    with WecomKfClient(http_client=httpx.Client(transport=httpx.MockTransport(handler))) as client:
        data = client.sync_msg("wkTEST", cursor="C1", token="T1")
        assert data["msg_list"]
        assert captured["body"]["open_kfid"] == "wkTEST"
        assert captured["body"]["token"] == "T1"
