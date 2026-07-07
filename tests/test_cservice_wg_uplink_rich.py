"""WeCom group rich uplink body tests (CS-34)."""

from __future__ import annotations

from app.db import get_session_factory
from app.services.wg_uplink_context import build_wg_uplink_body, sender_display_name
from tests.wg_helpers import seed_wg_group_session, seed_wg_inbound


def test_sender_display_name_suffix(tmp_cservice_db):
    assert sender_display_name("user_alice") == "用户·lice"
    assert sender_display_name("ab") == "用户·ab"


def test_wg_uplink_body_sections(tmp_cservice_db):
    factory = get_session_factory()
    db = factory()
    try:
        session, group = seed_wg_group_session(db)
        seed_wg_inbound(
            db,
            session_id=session.id,
            source_msgid="m1",
            content="请问体检报告怎么看？",
            sender_userid="user_alice",
        )
        body = build_wg_uplink_body(
            db,
            session=session,
            group=group,
            latest_sender_userid="user_alice",
        )
        assert "【群名称】测试健康群" in body
        assert "【智能机器人】数坤坤健康助手" in body
        assert "【发送者】" in body
        assert "【近期对话】" in body
        assert "【本轮待回复】" in body
        assert "请问体检报告怎么看？" in body
        assert "【起草要求】" in body
    finally:
        db.close()
