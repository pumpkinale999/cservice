"""WeCom group display_name enrichment tests."""

from __future__ import annotations

from unittest.mock import MagicMock

from app.models import WgGroup
from app.services.wg_group_display import (
    display_name_is_placeholder,
    enrich_group_display_names,
    refresh_group_display_name,
)


def test_display_name_is_placeholder():
    group = WgGroup(
        chatid="wrTEST001",
        ibot_id="ibot",
        display_name="群·TEST001",
        status="active",
        created_at="2026-07-07T10:00:00Z",
    )
    assert display_name_is_placeholder(group) is True
    group.display_name = "健康管理测试群"
    assert display_name_is_placeholder(group) is False


def test_refresh_from_payload():
    group = WgGroup(
        chatid="wrTEST001",
        ibot_id="ibot",
        display_name="群·TEST001",
        status="active",
        created_at="2026-07-07T10:00:00Z",
    )
    changed = refresh_group_display_name(
        group,
        {"group_display_name": "健康管理测试群"},
    )
    assert changed is True
    assert group.display_name == "健康管理测试群"


def test_refresh_from_wecom_api():
    group = WgGroup(
        chatid="wrTEST001",
        ibot_id="ibot",
        display_name="群·TEST001",
        status="active",
        created_at="2026-07-07T10:00:00Z",
    )
    client = MagicMock()
    client.groupchat_get.return_value = {
        "errcode": 0,
        "group_chat": {"name": "健康管理测试群"},
    }
    changed = refresh_group_display_name(group, {}, client=client)
    assert changed is True
    assert group.display_name == "健康管理测试群"
    client.groupchat_get.assert_called_once_with("wrTEST001")


def test_enrich_skips_named_groups():
    db = MagicMock()
    named = WgGroup(
        chatid="wr1",
        ibot_id="ibot",
        display_name="已有群名",
        status="active",
        created_at="2026-07-07T10:00:00Z",
    )
    client = MagicMock()
    enrich_group_display_names(db, client, [named])
    client.groupchat_get.assert_not_called()
