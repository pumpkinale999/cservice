"""WeCom aibot group outbound HTTP client (§5.6 · D-P4-13)."""

from __future__ import annotations

from typing import Any

import httpx

from app.config import Settings, get_settings
from app.services.wecom_errors import CserviceWecomError


class WecomAibotClient:
    """POST active `response_url` with text payload — no WSS / access_token."""

    def __init__(
        self,
        settings: Settings | None = None,
        *,
        http_client: httpx.Client | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self._http = http_client
        self._owns_client = http_client is None

    def _client(self) -> httpx.Client:
        if self._http is None:
            self._http = httpx.Client(timeout=15.0)
            self._owns_client = True
        return self._http

    def close(self) -> None:
        if self._owns_client and self._http is not None:
            self._http.close()
            self._http = None

    def __enter__(self) -> WecomAibotClient:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    def post_response(self, response_url: str, text: str) -> dict[str, Any]:
        """Send text reply via WeCom-provided one-shot response_url."""
        url = (response_url or "").strip()
        content = (text or "").strip()
        if not url:
            raise CserviceWecomError(-1, "missing response_url")
        if not content:
            raise CserviceWecomError(-1, "empty text")

        if self.settings.cservice_demo_outbound:
            return {"errcode": 0, "errmsg": "ok", "demo": True}

        body = {"msgtype": "text", "text": {"content": content}}
        resp = self._client().post(url, json=body)
        try:
            data = resp.json()
        except ValueError as exc:
            raise CserviceWecomError(-1, f"invalid json response: {resp.text[:200]}") from exc

        errcode = int(data.get("errcode", -1))
        if errcode != 0:
            raise CserviceWecomError(errcode, str(data.get("errmsg", "")))
        return data
