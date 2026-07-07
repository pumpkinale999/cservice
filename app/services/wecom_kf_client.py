"""WeCom kf HTTP client (§26.3 · mockable for tests)."""

from __future__ import annotations

import time
import uuid
from typing import Any

import httpx

from app.config import Settings, get_settings
from app.services.wecom_errors import CserviceWecomError

_TOKEN_CACHE: dict[str, Any] = {"token": "", "expires_at": 0.0}


class WecomKfClient:
    BASE = "https://qyapi.weixin.qq.com"

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

    def __enter__(self) -> WecomKfClient:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    def get_access_token(self, *, force_refresh: bool = False) -> str:
        global _TOKEN_CACHE
        now = time.time()
        if (
            not force_refresh
            and _TOKEN_CACHE["token"]
            and now < float(_TOKEN_CACHE["expires_at"]) - 60
        ):
            return str(_TOKEN_CACHE["token"])

        corp_id = self.settings.cservice_wecom_corp_id.strip()
        secret = self.settings.cservice_wecom_secret.strip()
        if not corp_id or not secret:
            raise CserviceWecomError(-1, "wecom not configured")

        resp = self._client().get(
            f"{self.BASE}/cgi-bin/gettoken",
            params={"corpid": corp_id, "corpsecret": secret},
        )
        data = resp.json()
        errcode = int(data.get("errcode", -1))
        if errcode != 0:
            raise CserviceWecomError(errcode, str(data.get("errmsg", "")))
        token = str(data["access_token"])
        expires_in = int(data.get("expires_in", 7200))
        _TOKEN_CACHE = {"token": token, "expires_at": now + expires_in}
        return token

    def _post_json(self, path: str, body: dict[str, Any]) -> dict[str, Any]:
        token = self.get_access_token()
        resp = self._client().post(
            f"{self.BASE}{path}",
            params={"access_token": token},
            json=body,
        )
        data = resp.json()
        errcode = int(data.get("errcode", -1))
        if errcode != 0:
            raise CserviceWecomError(errcode, str(data.get("errmsg", "")))
        return data

    def sync_msg(
        self,
        open_kfid: str,
        *,
        cursor: str | None = None,
        token: str | None = None,
        limit: int = 1000,
    ) -> dict[str, Any]:
        body: dict[str, Any] = {"open_kfid": open_kfid, "limit": limit}
        if cursor:
            body["cursor"] = cursor
        if token:
            body["token"] = token
        return self._post_json("/cgi-bin/kf/sync_msg", body)

    def service_state_get(self, open_kfid: str, external_userid: str) -> dict[str, Any]:
        return self._post_json(
            "/cgi-bin/kf/service_state/get",
            {"open_kfid": open_kfid, "external_userid": external_userid},
        )

    def service_state_trans(
        self,
        open_kfid: str,
        external_userid: str,
        servicer_userid: str,
        *,
        service_state: int = 3,
    ) -> dict[str, Any]:
        return self._post_json(
            "/cgi-bin/kf/service_state/trans",
            {
                "open_kfid": open_kfid,
                "external_userid": external_userid,
                "service_state": service_state,
                "servicer_userid": servicer_userid,
            },
        )

    def customer_batchget(
        self,
        external_userid_list: list[str],
        *,
        need_enter_session_context: int = 0,
    ) -> dict[str, Any]:
        if not external_userid_list:
            return {"errcode": 0, "errmsg": "ok", "customer_list": []}
        return self._post_json(
            "/cgi-bin/kf/customer/batchget",
            {
                "external_userid_list": external_userid_list,
                "need_enter_session_context": need_enter_session_context,
            },
        )

    def send_text_msg(
        self,
        open_kfid: str,
        external_userid: str,
        content: str,
        *,
        msgid: str | None = None,
    ) -> dict[str, Any]:
        corp_id = self.settings.cservice_wecom_corp_id.strip()
        secret = self.settings.cservice_wecom_secret.strip()
        if self.settings.cservice_demo_outbound and (not corp_id or not secret):
            return {
                "errcode": 0,
                "msgid": msgid or f"demo-{uuid.uuid4().hex[:16]}",
            }
        body: dict[str, Any] = {
            "touser": external_userid,
            "open_kfid": open_kfid,
            "msgtype": "text",
            "text": {"content": content},
        }
        if msgid:
            body["msgid"] = msgid
        return self._post_json("/cgi-bin/kf/send_msg", body)

    def servicer_list(self, open_kfid: str) -> dict[str, Any]:
        return self._post_json(
            "/cgi-bin/kf/servicer/list",
            {"open_kfid": open_kfid},
        )

    def servicer_add(self, open_kfid: str, userid_list: list[str]) -> dict[str, Any]:
        if not userid_list:
            return {"errcode": 0, "errmsg": "ok", "result_list": []}
        return self._post_json(
            "/cgi-bin/kf/servicer/add",
            {"open_kfid": open_kfid, "userid_list": userid_list},
        )

    def servicer_del(self, open_kfid: str, userid_list: list[str]) -> dict[str, Any]:
        if not userid_list:
            return {"errcode": 0, "errmsg": "ok", "result_list": []}
        return self._post_json(
            "/cgi-bin/kf/servicer/del",
            {"open_kfid": open_kfid, "userid_list": userid_list},
        )

    def groupchat_get(self, chat_id: str) -> dict[str, Any]:
        """Fetch customer group detail (name, members) by chat_id."""
        return self._post_json(
            "/cgi-bin/externalcontact/groupchat/get",
            {"chat_id": chat_id, "need_name": 0},
        )


def reset_token_cache() -> None:
    global _TOKEN_CACHE
    _TOKEN_CACHE = {"token": "", "expires_at": 0.0}


def probe_wecom_token(settings: Settings | None = None) -> str:
    """Return ok | error | not_configured for health."""
    settings = settings or get_settings()
    if not settings.cservice_wecom_corp_id or not settings.cservice_wecom_secret:
        return "not_configured"
    try:
        with WecomKfClient(settings) as client:
            client.get_access_token(force_refresh=True)
        return "ok"
    except CserviceWecomError:
        return "error"
