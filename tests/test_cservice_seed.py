"""Seed loader tests (M1 · PR-2)."""

from __future__ import annotations

from pathlib import Path

from app.db import get_session_factory
from app.models import KfAccount, KfServicer, SceneRoute
from app.services.seed import load_seed_file

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "cservice"


def test_load_seed_minimal(tmp_cservice_db):
    factory = get_session_factory()
    session = factory()
    try:
        counts = load_seed_file(FIXTURES / "seed_minimal.yaml", session)
        assert counts == {"kf_accounts": 1, "kf_servicers": 1, "scene_routes": 1}

        account = session.get(KfAccount, "wkTEST_MINIMAL")
        assert account is not None
        assert account.display_name == "测试账号"

        servicer = (
            session.query(KfServicer)
            .filter_by(open_kfid="wkTEST_MINIMAL", servicer_userid="zhangsan")
            .one()
        )
        assert servicer.sort_order == 0

        route = (
            session.query(SceneRoute)
            .filter_by(open_kfid="wkTEST_MINIMAL", scene="官网")
            .one()
        )
        assert route.servicer_userid == "lisi"
    finally:
        session.close()


def test_load_seed_idempotent(tmp_cservice_db):
    factory = get_session_factory()
    session = factory()
    path = FIXTURES / "seed_minimal.yaml"
    try:
        load_seed_file(path, session)
        load_seed_file(path, session)

        assert session.query(KfAccount).count() == 1
        assert session.query(KfServicer).count() == 1
        assert session.query(SceneRoute).count() == 1
    finally:
        session.close()
