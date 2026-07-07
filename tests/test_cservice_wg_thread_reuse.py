"""WeCom group agent thread reuse tests (CS-32)."""

from __future__ import annotations

from app.db import get_session_factory
from app.models import WgAgentThread
from app.services.wg_agent_thread import ensure_wg_agent_thread
from tests.wg_helpers import seed_wg_group_session


def test_wg_thread_reused_for_same_chat(tmp_cservice_db):
    factory = get_session_factory()
    db = factory()
    try:
        session, group = seed_wg_group_session(db)
        t1 = ensure_wg_agent_thread(
            db,
            ibot_id=group.ibot_id,
            chatid=group.chatid,
            session=session,
        )
        t2 = ensure_wg_agent_thread(
            db,
            ibot_id=group.ibot_id,
            chatid=group.chatid,
            session=session,
        )
        db.commit()
        assert t1.id == t2.id
        assert db.query(WgAgentThread).count() == 1
    finally:
        db.close()
