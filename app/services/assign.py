"""Session assignment (§8.1 · §17.2)."""

from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from app.models import KfAccount, KfServicer, SceneRoute, Session as CSession
from app.services.agent_thread import ensure_agent_thread
from app.services.assign_retry import clear_assign_retry, record_assign_failure
from app.services.wecom_errors import CserviceWecomError
from app.services.wecom_kf_client import WecomKfClient

logger = logging.getLogger(__name__)


def pick_servicer(
    session: Session,
    open_kfid: str,
    scene: str | None = None,
) -> str | None:
    if scene:
        route = (
            session.query(SceneRoute)
            .filter_by(open_kfid=open_kfid, scene=scene)
            .one_or_none()
        )
        if route is not None:
            return route.servicer_userid

    servicers = (
        session.query(KfServicer)
        .filter_by(open_kfid=open_kfid)
        .order_by(KfServicer.sort_order.asc())
        .all()
    )
    if not servicers:
        return None

    account = session.get(KfAccount, open_kfid)
    if account is None:
        return servicers[0].servicer_userid

    idx = account.last_assigned_index % len(servicers)
    picked = servicers[idx].servicer_userid
    account.last_assigned_index = (idx + 1) % len(servicers)
    return picked


def assign_session_if_needed(
    db: Session,
    csession: CSession,
    external_userid: str,
    *,
    scene: str | None,
    client: WecomKfClient,
) -> None:
    if csession.servicer_userid:
        ensure_agent_thread(db, csession, external_userid)
        return

    servicer = pick_servicer(db, csession.open_kfid, scene)
    if not servicer:
        csession.status = "unassigned"
        logger.warning("no servicer for open_kfid=%s", csession.open_kfid)
        return

    try:
        client.service_state_get(csession.open_kfid, external_userid)
        client.service_state_trans(
            csession.open_kfid,
            external_userid,
            servicer,
            service_state=3,
        )
    except CserviceWecomError as exc:
        record_assign_failure(db, csession, exc.errcode)
        # 本地先绑定接待，便于 UI 可见；企微 trans 由 assign_retry 后续重试
        csession.servicer_userid = servicer
        csession.status = "open"
        ensure_agent_thread(db, csession, external_userid)
        logger.warning(
            "assign trans deferred open_kfid=%s servicer=%s errcode=%s",
            csession.open_kfid,
            servicer,
            exc.errcode,
        )
        return

    csession.servicer_userid = servicer
    csession.status = "open"
    clear_assign_retry(db, csession.id)
    ensure_agent_thread(db, csession, external_userid)
