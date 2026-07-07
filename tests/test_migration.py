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


def test_migration_m7_columns(tmp_cservice_db):
    from sqlalchemy import inspect

    from app.db import get_engine

    insp = inspect(get_engine())
    servicer_cols = {c["name"] for c in insp.get_columns("cservice_kf_servicer")}
    assert "user_id" in servicer_cols
    assert "enabled" in servicer_cols
    pk = insp.get_pk_constraint("cservice_kf_servicer")
    assert set(pk["constrained_columns"]) == {"open_kfid", "user_id"}


def test_migration_m6_columns(tmp_cservice_db):
    from sqlalchemy import inspect

    from app.db import get_engine

    insp = inspect(get_engine())
    draft_cols = {c["name"] for c in insp.get_columns("cservice_draft")}
    assert "version" in draft_cols
    thread_cols = {c["name"] for c in insp.get_columns("cservice_agent_thread")}
    assert "uplink_pending" in thread_cols
    assert "uplink_started_at" in thread_cols


P4_WG_TABLES = (
    "cservice_wg_group",
    "cservice_wg_session",
    "cservice_wg_message",
    "cservice_wg_draft",
    "cservice_wg_audit_log",
    "cservice_wg_agent_thread",
    "cservice_wg_reply_anchor",
    "cservice_wg_ingress_dedup",
    "cservice_wg_uplink_retry",
)


def test_migration_p4_wg_tables(tmp_cservice_db):
    from sqlalchemy import inspect

    from app.db import get_engine

    for name in P4_WG_TABLES:
        assert table_exists(name), name

    insp = inspect(get_engine())
    thread_cols = {c["name"] for c in insp.get_columns("cservice_wg_agent_thread")}
    assert {"ibot_id", "chatid", "uplink_pending"}.issubset(thread_cols)
    uqs = insp.get_unique_constraints("cservice_wg_agent_thread")
    assert any(set(uq.get("column_names") or []) == {"ibot_id", "chatid"} for uq in uqs)
