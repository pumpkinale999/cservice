"""Kf servicer admin — DB + WeCom sync (M7 · §17.5)."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from sqlalchemy.orm import Session

from app.models import KfAccount, KfServicer
from app.services.wecom_kf_client import WecomKfClient

logger = logging.getLogger(__name__)


@dataclass
class ServicerInput:
    user_id: str
    sort_order: int
    servicer_userid: str


@dataclass
class ServicerSyncResult:
    user_id: str
    servicer_userid: str
    action: str
    errcode: int
    errmsg: str


def is_user_participant(db: Session, user_id: str) -> bool:
    uid = user_id.strip()
    if not uid:
        return False
    return (
        db.query(KfServicer)
        .filter(KfServicer.user_id == uid, KfServicer.enabled.is_(True))
        .first()
        is not None
    )


def list_kf_accounts(db: Session) -> list[dict[str, Any]]:
    rows = db.query(KfAccount).order_by(KfAccount.display_name.asc()).all()
    return [
        {
            "open_kfid": row.open_kfid,
            "display_name": row.display_name,
            "api_managed": bool(row.api_managed),
        }
        for row in rows
    ]


def list_servicers_for_kf(db: Session, open_kfid: str) -> list[KfServicer]:
    return (
        db.query(KfServicer)
        .filter_by(open_kfid=open_kfid)
        .order_by(KfServicer.sort_order.asc(), KfServicer.user_id.asc())
        .all()
    )


def replace_servicers(
    db: Session,
    open_kfid: str,
    servicers: list[ServicerInput],
    client: WecomKfClient,
) -> list[ServicerSyncResult]:
    account = db.get(KfAccount, open_kfid)
    if account is None:
        raise ValueError(f"unknown open_kfid: {open_kfid}")

    existing = {
        row.user_id: row
        for row in db.query(KfServicer).filter_by(open_kfid=open_kfid).all()
    }
    desired = {s.user_id: s for s in servicers}

    # Remove rows not in desired set
    for uid, row in list(existing.items()):
        if uid not in desired:
            db.delete(row)

    # Upsert desired
    for item in sorted(servicers, key=lambda s: (s.sort_order, s.user_id)):
        row = existing.get(item.user_id)
        if row is None:
            db.add(
                KfServicer(
                    open_kfid=open_kfid,
                    user_id=item.user_id,
                    servicer_userid=item.servicer_userid,
                    sort_order=item.sort_order,
                    enabled=True,
                )
            )
        else:
            row.servicer_userid = item.servicer_userid
            row.sort_order = item.sort_order
            row.enabled = True

    db.flush()

    return _sync_wecom_servicers(db, open_kfid, client)


def _sync_wecom_servicers(
    db: Session,
    open_kfid: str,
    client: WecomKfClient,
) -> list[ServicerSyncResult]:
    """Diff cservice DB vs WeCom and apply add/del. Returns per-user results."""
    db_rows = list_servicers_for_kf(db, open_kfid)
    db_userids = {row.servicer_userid for row in db_rows if row.enabled}

    try:
        wx_data = client.servicer_list(open_kfid)
        wx_userids = set(_extract_wx_servicer_userids(wx_data))
    except Exception as exc:
        logger.warning("servicer_list failed open_kfid=%s: %s", open_kfid, exc)
        wx_userids = set()

    to_add = sorted(db_userids - wx_userids)
    to_del = sorted(wx_userids - db_userids)

    results: list[ServicerSyncResult] = []

    if to_add:
        try:
            add_resp = client.servicer_add(open_kfid, to_add)
            results.extend(_parse_wx_result_list(add_resp, "add", db_rows))
        except Exception as exc:
            for row in db_rows:
                if row.servicer_userid in to_add:
                    results.append(
                        ServicerSyncResult(
                            user_id=row.user_id,
                            servicer_userid=row.servicer_userid,
                            action="add",
                            errcode=-1,
                            errmsg=str(exc),
                        )
                    )

    if to_del:
        try:
            del_resp = client.servicer_del(open_kfid, to_del)
            results.extend(_parse_wx_result_list(del_resp, "del", db_rows, userid_filter=to_del))
        except Exception as exc:
            for wx_uid in to_del:
                results.append(
                    ServicerSyncResult(
                        user_id=_userid_for_wx(db_rows, wx_uid),
                        servicer_userid=wx_uid,
                        action="del",
                        errcode=-1,
                        errmsg=str(exc),
                    )
                )

    # Success rows for unchanged / already synced
    touched = {(r.servicer_userid, r.action) for r in results}
    for row in db_rows:
        if row.servicer_userid in wx_userids & db_userids:
            key_add = (row.servicer_userid, "add")
            key_del = (row.servicer_userid, "del")
            if key_add not in touched and key_del not in touched:
                results.append(
                    ServicerSyncResult(
                        user_id=row.user_id,
                        servicer_userid=row.servicer_userid,
                        action="noop",
                        errcode=0,
                        errmsg="ok",
                    )
                )

    db.commit()
    return results


def _extract_wx_servicer_userids(data: dict[str, Any]) -> list[str]:
    servicer_list = data.get("servicer_list") or []
    userids: list[str] = []
    for item in servicer_list:
        if isinstance(item, dict):
            uid = item.get("userid") or item.get("servicer_userid")
            if uid:
                userids.append(str(uid))
        elif isinstance(item, str):
            userids.append(item)
    return userids


def _userid_for_wx(rows: list[KfServicer], servicer_userid: str) -> str:
    for row in rows:
        if row.servicer_userid == servicer_userid:
            return row.user_id
    return servicer_userid


def _parse_wx_result_list(
    data: dict[str, Any],
    action: str,
    db_rows: list[KfServicer],
    *,
    userid_filter: list[str] | None = None,
) -> list[ServicerSyncResult]:
    out: list[ServicerSyncResult] = []
    result_list = data.get("result_list") or []
    if result_list:
        for item in result_list:
            wx_uid = str(item.get("userid") or item.get("servicer_userid") or "")
            if userid_filter is not None and wx_uid not in userid_filter:
                continue
            out.append(
                ServicerSyncResult(
                    user_id=_userid_for_wx(db_rows, wx_uid),
                    servicer_userid=wx_uid,
                    action=action,
                    errcode=int(item.get("errcode", 0)),
                    errmsg=str(item.get("errmsg", "ok")),
                )
            )
        return out

    # Whole-call success without per-user breakdown
    errcode = int(data.get("errcode", 0))
    errmsg = str(data.get("errmsg", "ok"))
    targets = userid_filter or [row.servicer_userid for row in db_rows]
    for wx_uid in targets:
        out.append(
            ServicerSyncResult(
                user_id=_userid_for_wx(db_rows, wx_uid),
                servicer_userid=wx_uid,
                action=action,
                errcode=errcode,
                errmsg=errmsg,
            )
        )
    return out
