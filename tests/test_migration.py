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
)


def test_migration_all_tables(tmp_cservice_db):
    for name in ALL_MVP_TABLES:
        assert table_exists(name), name
