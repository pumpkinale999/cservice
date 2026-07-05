"""WeCom kf webhook routes (§20)."""

from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, Query, Request
from fastapi.responses import PlainTextResponse

from app.config import get_settings
from app.db import get_session_factory
from app.services.kf_webhook_handler import handle_kf_event_plain
from app.services.wecom_kf_crypto import WecomKfCrypt, WecomKfCryptError

router = APIRouter(prefix="/cservice/kf", tags=["cservice-kf"])


def _crypt() -> WecomKfCrypt:
    s = get_settings()
    return WecomKfCrypt(
        token=s.cservice_kf_callback_token,
        encoding_aes_key=s.cservice_kf_callback_aes_key,
        corp_id=s.cservice_wecom_corp_id,
    )


@router.get("/callback")
def kf_callback_verify(
    msg_signature: str = Query(...),
    timestamp: str = Query(...),
    nonce: str = Query(...),
    echostr: str = Query(...),
) -> PlainTextResponse:
    try:
        plain = _crypt().verify_url(msg_signature, timestamp, nonce, echostr)
    except WecomKfCryptError:
        return PlainTextResponse("invalid signature", status_code=403)
    return PlainTextResponse(plain)


@router.post("/callback")
async def kf_callback_event(
    request: Request,
    background_tasks: BackgroundTasks,
    msg_signature: str = Query(...),
    timestamp: str = Query(...),
    nonce: str = Query(...),
) -> PlainTextResponse:
    body = (await request.body()).decode("utf-8")
    try:
        plain = _crypt().decrypt_post(msg_signature, timestamp, nonce, body)
    except WecomKfCryptError:
        return PlainTextResponse("invalid signature", status_code=403)

    def _process() -> None:
        factory = get_session_factory()
        db = factory()
        try:
            handle_kf_event_plain(db, plain)
        finally:
            db.close()

    background_tasks.add_task(_process)
    return PlainTextResponse("success")
