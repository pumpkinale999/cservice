"""群主动发送的结构化错误（gateway / 企微 errcode → detail.code）。"""

from __future__ import annotations

from typing import Any

from fastapi import HTTPException, status

from app.services.wecom_errors import CserviceWecomError

# HTTP response_url errors
_RESPONSE_URL_CONSUMED = frozenset({60140})
_NO_SESSION_ERRCODES = frozenset({600039})


def classify_wecom_errcode(errcode: int, *, via: str = "wss") -> str:
    """Map WeCom errcode to stable cservice detail.code."""
    if errcode in _RESPONSE_URL_CONSUMED:
        return "anchor_consumed"
    if errcode in _NO_SESSION_ERRCODES:
        return "wecom_no_session"
    return "wecom_error"


def raise_for_wecom_error(exc: CserviceWecomError) -> None:
    code = classify_wecom_errcode(exc.errcode, via="response_url")
    raise HTTPException(
        status_code=status.HTTP_502_BAD_GATEWAY,
        detail={
            "code": code,
            "errcode": exc.errcode,
            "errmsg": exc.errmsg,
        },
    ) from exc


def raise_for_group_send_result(result: dict[str, Any]) -> None:
    """主动发送失败时抛出 HTTPException（WSS 回执 ok=false）。"""
    if result.get("ok"):
        return

    code = str(result.get("code") or "send_failed").strip() or "send_failed"
    errcode = result.get("errcode")
    errmsg = str(result.get("errmsg") or "").strip()

    if code == "gateway_offline":
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "code": "gateway_offline",
                "message": "Bot 网关未连接，无法发送到群。请确认 hermes-gateway-cservice-assistant 已启动。",
            },
        )
    if code == "send_timeout":
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail={
                "code": "send_timeout",
                "message": "网关发送超时，请稍后重试。",
            },
        )
    if code == "wecom_not_connected":
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "code": "wecom_not_connected",
                "message": "Bot 与企微长连接未就绪，请稍后重试或重启 cservice-assistant 网关。",
            },
        )
    if code == "wecom_no_session":
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={
                "code": "wecom_no_session",
                "errcode": errcode,
                "errmsg": errmsg,
                "message": "企微拒绝发送：该群 24 小时内需有人 @ Bot 建立会话后才能主动推送。",
            },
        )
    if code == "wecom_error":
        mapped = classify_wecom_errcode(int(errcode), via="wss") if errcode is not None else "wecom_error"
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={
                "code": mapped,
                "errcode": errcode,
                "errmsg": errmsg,
            },
        )
    raise HTTPException(
        status_code=status.HTTP_502_BAD_GATEWAY,
        detail={"code": code, "errcode": errcode, "errmsg": errmsg},
    )
