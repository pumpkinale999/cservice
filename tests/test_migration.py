from app.db import table_exists

ALL_MVP_TABLES = (
    "cservice_kf_account",
    "cservice_kf_servicer",
    "cservice_scene_route",
    "cservice_customer",
    "cservice_session",
    "cservice_agent_thread",
    "cservice_message",
    "cservice_draft",
    "cservice_audit_log",
    "cservice_sync_state",
    "cservice_webhook_dedup",
    "cservice_assign_retry",
    "cservice_uplink_retry",
    "cservice_event_log",
)


def test_migration_all_tables(tmp_cservice_db):
    for name in ALL_MVP_TABLES:
        assert table_exists(name), name


def test_migration_m6_columns(tmp_cservice_db):
    from sqlalchemy import inspect

    from app.db import get_engine

    insp = inspect(get_engine())
    draft_cols = {c["name"] for c in insp.get_columns("cservice_draft")}
    assert "version" in draft_cols
    thread_cols = {c["name"] for c in insp.get_columns("cservice_agent_thread")}
    assert "uplink_pending" in thread_cols
    assert "uplink_started_at" in thread_cols
