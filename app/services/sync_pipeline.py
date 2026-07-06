"""sync_msg pipeline (§21)."""

from __future__ import annotations

import logging
import threading
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.models import Customer, SyncState
from app.services.assign import assign_session_if_needed
from app.services.customer_display import (
    display_name_is_placeholder,
    enrich_customer_display_names,
)
from app.services.ingress_filter import record_skipped_ingress, should_skip_customer_ingress
from app.services.message_ingest import ingest_sync_message, message_item_scene
from app.services.send_fail_handler import apply_msg_send_fail
from app.services.uplink_hook import HermesUplinkHook, NoopUplinkHook, UplinkHook
from app.services.wecom_kf_client import WecomKfClient

logger = logging.getLogger(__name__)

_KF_LOCKS: dict[str, threading.Lock] = {}
_KF_LOCKS_GUARD = threading.Lock()


@dataclass
class _PendingUplink:
    session_id: str
    thread_id: int
    text: str
    wx_msgid: str
    open_kfid: str
    external_userid: str


def _lock_for_kf(open_kfid: str) -> threading.Lock:
    with _KF_LOCKS_GUARD:
        if open_kfid not in _KF_LOCKS:
            _KF_LOCKS[open_kfid] = threading.Lock()
        return _KF_LOCKS[open_kfid]


def _now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def _get_cursor(db: Session, open_kfid: str) -> str | None:
    row = db.get(SyncState, open_kfid)
    return row.cursor if row else None


def _save_cursor(db: Session, open_kfid: str, cursor: str) -> None:
    row = db.get(SyncState, open_kfid)
    if row is None:
        db.add(
            SyncState(
                open_kfid=open_kfid,
                cursor=cursor,
                updated_at=_now(),
            )
        )
    else:
        row.cursor = cursor
        row.updated_at = _now()


def run_sync_for_kf(
    db: Session,
    open_kfid: str,
    *,
    token: str | None,
    client: WecomKfClient,
    uplink_hook: UplinkHook | None = None,
) -> None:
    uplink = uplink_hook if uplink_hook is not None else NoopUplinkHook()
    cursor = _get_cursor(db, open_kfid)
    has_more = 1
    while has_more:
        data = client.sync_msg(open_kfid, cursor=cursor, token=token)
        msg_list = sorted(
            data.get("msg_list") or [],
            key=lambda m: int(m.get("send_time", 0)),
        )
        pending_uplink: _PendingUplink | None = None
        customers_needing_display: dict[str, Customer] = {}
        for item in msg_list:
            if str(item.get("event_type") or "") == "msg_send_fail":
                apply_msg_send_fail(db, item)
                continue
            if should_skip_customer_ingress(item):
                record_skipped_ingress(db, item, open_kfid)
                continue
            csession, customer, is_new = ingest_sync_message(db, item, open_kfid)
            if display_name_is_placeholder(customer):
                customers_needing_display[customer.external_userid] = customer
            if not is_new:
                continue
            external_userid = str(item.get("external_userid", customer.external_userid))
            scene = message_item_scene(item)
            assign_session_if_needed(
                db,
                csession,
                external_userid,
                scene=scene,
                client=client,
            )
            origin = int(item.get("origin", 3))
            msgtype = str(item.get("msgtype", "text"))
            if origin == 3 and msgtype == "text" and csession.servicer_userid:
                thread = csession.agent_thread
                if thread is not None:
                    text = str((item.get("text") or {}).get("content", ""))
                    pending_uplink = _PendingUplink(
                        session_id=csession.id,
                        thread_id=thread.id,
                        text=text,
                        wx_msgid=str(item.get("msgid", "")),
                        open_kfid=open_kfid,
                        external_userid=external_userid,
                    )
        enrich_customer_display_names(
            db,
            client,
            list(customers_needing_display.values()),
        )
        db.commit()

        if pending_uplink is not None:
            uplink.on_text_inbound(
                pending_uplink.session_id,
                pending_uplink.thread_id,
                pending_uplink.text,
                pending_uplink.wx_msgid,
                open_kfid=pending_uplink.open_kfid,
                external_userid=pending_uplink.external_userid,
            )

        next_cursor = data.get("next_cursor") or cursor
        if next_cursor:
            _save_cursor(db, open_kfid, str(next_cursor))
        db.commit()
        has_more = int(data.get("has_more", 0))
        cursor = str(next_cursor) if next_cursor else cursor
        token = None


def run_sync_job(open_kfid: str, token: str | None, client: WecomKfClient) -> None:
    from app.db import get_session_factory

    lock = _lock_for_kf(open_kfid)
    with lock:
        factory = get_session_factory()
        db = factory()
        try:
            run_sync_for_kf(
                db,
                open_kfid,
                token=token,
                client=client,
                uplink_hook=HermesUplinkHook(),
            )
        finally:
            db.close()
