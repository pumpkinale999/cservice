"""WecomAibotClient unit tests."""

from __future__ import annotations

from unittest.mock import MagicMock

import httpx
import pytest

from app.config import get_settings
from app.services.wecom_aibot_client import WecomAibotClient
from app.services.wecom_errors import CserviceWecomError


def test_post_response_demo_mode(monkeypatch):
    monkeypatch.setenv("CSERVICE_DEMO_OUTBOUND", "1")
    get_settings.cache_clear()

    with WecomAibotClient() as client:
        result = client.post_response("https://example.com/r", "hello")
    assert result["errcode"] == 0
    assert result.get("demo") is True
    get_settings.cache_clear()


def test_post_response_empty_url():
    with WecomAibotClient() as client:
        with pytest.raises(CserviceWecomError, match="missing response_url"):
            client.post_response("", "hello")


def test_post_response_empty_text():
    with WecomAibotClient() as client:
        with pytest.raises(CserviceWecomError, match="empty text"):
            client.post_response("https://example.com/r", "  ")


def test_post_response_http_success():
    mock_http = MagicMock(spec=httpx.Client)
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"errcode": 0, "errmsg": "ok"}
    mock_http.post.return_value = mock_resp

    with WecomAibotClient(http_client=mock_http) as client:
        result = client.post_response("https://example.com/r", "hi there")

    assert result["errcode"] == 0
    mock_http.post.assert_called_once_with(
        "https://example.com/r",
        json={"msgtype": "markdown", "markdown": {"content": "hi there"}},
    )


def test_post_response_wecom_error():
    mock_http = MagicMock(spec=httpx.Client)
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"errcode": 40001, "errmsg": "invalid"}
    mock_http.post.return_value = mock_resp

    with WecomAibotClient(http_client=mock_http) as client:
        with pytest.raises(CserviceWecomError) as exc:
            client.post_response("https://example.com/r", "hi")
    assert exc.value.errcode == 40001
