"""CS-20: agent thread reuse across sessions."""

from __future__ import annotations

import copy

from app.db import get_session_factory
from app.models import AgentThread, Session as CSession
from app.services.sync_pipeline import run_sync_for_kf
from tests.conftest import build_mock_wecom_client, load_json_fixture


def test_thread_reused_when_session_closed_and_reopened(loaded_seed, wecom_env):
    first = load_json_fixture("sync_msg_text_inbound.json")
    second = copy.deepcopy(first)
    second["msg_list"][0]["msgid"] = "msg_inbound_002"
    second["msg_list"][0]["text"] = {"content": "再次咨询"}
    client = build_mock_wecom_client(sync_responses=[first, second])
    factory = get_session_factory()
    db = factory()
    try:
        run_sync_for_kf(db, "wkTEST_MINIMAL", token="T1", client=client)
        thread = db.query(AgentThread).one()
        first_thread_id = thread.id
        first_session_id = thread.session_id
        csession = db.get(CSession, first_session_id)
        csession.status = "closed"
        db.commit()

        run_sync_for_kf(db, "wkTEST_MINIMAL", token="T2", client=client)
        threads = db.query(AgentThread).all()
        assert len(threads) == 1
        assert threads[0].id == first_thread_id
        assert threads[0].session_id != first_session_id
        open_sessions = (
            db.query(CSession)
            .filter_by(open_kfid="wkTEST_MINIMAL", status="open")
            .all()
        )
        assert len(open_sessions) == 1
        assert threads[0].session_id == open_sessions[0].id
    finally:
        db.close()
