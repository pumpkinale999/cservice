"""Load cservice seed YAML into DB (§27.4)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from sqlalchemy.orm import Session

from app.models import KfAccount, KfServicer, SceneRoute


def _parse_bool(value: Any) -> int:
    if isinstance(value, bool):
        return 1 if value else 0
    if isinstance(value, int):
        return 1 if value else 0
    if isinstance(value, str):
        return 1 if value.lower() in ("1", "true", "yes") else 0
    return 0


def _parse_enabled(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return value != 0
    if isinstance(value, str):
        return value.lower() in ("1", "true", "yes")
    return True


def load_seed_data(data: dict[str, Any], session: Session) -> dict[str, int]:
    """Upsert kf_accounts, kf_servicers, scene_routes. Returns row counts."""
    counts = {"kf_accounts": 0, "kf_servicers": 0, "scene_routes": 0}

    for item in data.get("kf_accounts") or []:
        open_kfid = str(item["open_kfid"])
        row = session.get(KfAccount, open_kfid)
        if row is None:
            row = KfAccount(
                open_kfid=open_kfid,
                display_name=str(item.get("display_name") or open_kfid),
                api_managed=_parse_bool(item.get("api_managed", True)),
                last_assigned_index=int(item.get("last_assigned_index") or 0),
            )
            session.add(row)
        else:
            row.display_name = str(item.get("display_name") or row.display_name)
            row.api_managed = _parse_bool(item.get("api_managed", row.api_managed))
            row.last_assigned_index = int(
                item.get("last_assigned_index", row.last_assigned_index)
            )
        counts["kf_accounts"] += 1

    session.flush()

    for item in data.get("kf_servicers") or []:
        open_kfid = str(item["open_kfid"])
        servicer_userid = str(item["servicer_userid"])
        user_id = str(item.get("user_id") or servicer_userid)
        row = (
            session.query(KfServicer)
            .filter_by(open_kfid=open_kfid, user_id=user_id)
            .one_or_none()
        )
        if row is None:
            session.add(
                KfServicer(
                    open_kfid=open_kfid,
                    user_id=user_id,
                    servicer_userid=servicer_userid,
                    sort_order=int(item.get("sort_order") or 0),
                    enabled=_parse_enabled(item.get("enabled")),
                )
            )
        else:
            row.servicer_userid = servicer_userid
            row.sort_order = int(item.get("sort_order", row.sort_order))
            row.enabled = _parse_enabled(item.get("enabled", row.enabled))
        counts["kf_servicers"] += 1

    for item in data.get("scene_routes") or []:
        open_kfid = str(item["open_kfid"])
        scene = str(item["scene"])
        row = (
            session.query(SceneRoute)
            .filter_by(open_kfid=open_kfid, scene=scene)
            .one_or_none()
        )
        if row is None:
            session.add(
                SceneRoute(
                    open_kfid=open_kfid,
                    scene=scene,
                    servicer_userid=str(item["servicer_userid"]),
                )
            )
        else:
            row.servicer_userid = str(item["servicer_userid"])
        counts["scene_routes"] += 1

    session.commit()
    return counts


def load_seed_file(path: Path, session: Session) -> dict[str, int]:
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError(f"seed file must be a YAML mapping: {path}")
    return load_seed_data(raw, session)
