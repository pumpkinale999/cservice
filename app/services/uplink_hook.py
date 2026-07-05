"""Uplink hook — M2 Noop · M3 Hermes."""

from __future__ import annotations

from typing import Protocol


class UplinkHook(Protocol):
    def on_text_inbound(
        self,
        session_id: str,
        thread_id: int,
        text: str,
        wx_msgid: str,
        *,
        open_kfid: str = "",
        external_userid: str = "",
    ) -> None: ...


class NoopUplinkHook:
    def on_text_inbound(self, *args: object, **kwargs: object) -> None:
        return None


class HermesUplinkHook:
    def on_text_inbound(
        self,
        session_id: str,
        thread_id: int,
        text: str,
        wx_msgid: str,
        *,
        open_kfid: str = "",
        external_userid: str = "",
    ) -> None:
        from app.db import get_session_factory
        from app.hermes.uplink_queue import enqueue_uplink

        factory = get_session_factory()
        db = factory()
        try:
            enqueue_uplink(
                db,
                session_id=session_id,
                thread_id=thread_id,
                open_kfid=open_kfid,
                external_userid=external_userid,
                text=text,
                trigger_wx_msgid=wx_msgid,
                supersede=True,
            )
            db.commit()
        finally:
            db.close()
