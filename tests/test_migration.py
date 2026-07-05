from app.db import table_exists


def test_migration_tables(tmp_cservice_db):
    for name in (
        "cservice_kf_account",
        "cservice_session",
        "cservice_message",
        "cservice_draft",
        "cservice_webhook_dedup",
    ):
        assert table_exists(name), name
