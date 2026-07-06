"""M7: kf_servicer user_id PK + enabled (§28.4.2).

Revision ID: 004_cservice_m7_servicer_user_id
Revises: 003_cservice_m6
Create Date: 2026-07-06
"""

from __future__ import annotations

from alembic import op

revision = "004_cservice_m7_servicer_user_id"
down_revision = "003_cservice_m6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # SQLite: recreate table with (open_kfid, user_id) PK.
    # Backfill: user_id = servicer_userid until skstudio users mapping script runs.
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS cservice_kf_servicer_m7 (
          open_kfid TEXT NOT NULL REFERENCES cservice_kf_account(open_kfid),
          user_id TEXT NOT NULL,
          servicer_userid TEXT NOT NULL,
          sort_order INTEGER NOT NULL DEFAULT 0,
          enabled INTEGER NOT NULL DEFAULT 1,
          PRIMARY KEY (open_kfid, user_id)
        )
        """
    )
    op.execute(
        """
        INSERT INTO cservice_kf_servicer_m7 (open_kfid, user_id, servicer_userid, sort_order, enabled)
        SELECT open_kfid, servicer_userid, servicer_userid, sort_order, 1
        FROM cservice_kf_servicer
        """
    )
    op.execute("DROP TABLE cservice_kf_servicer")
    op.execute("ALTER TABLE cservice_kf_servicer_m7 RENAME TO cservice_kf_servicer")
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_cservice_kf_servicer_user_id ON cservice_kf_servicer (user_id)"
    )


def downgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS cservice_kf_servicer_legacy (
          open_kfid TEXT NOT NULL REFERENCES cservice_kf_account(open_kfid),
          servicer_userid TEXT NOT NULL,
          sort_order INTEGER NOT NULL DEFAULT 0,
          PRIMARY KEY (open_kfid, servicer_userid)
        )
        """
    )
    op.execute(
        """
        INSERT INTO cservice_kf_servicer_legacy (open_kfid, servicer_userid, sort_order)
        SELECT open_kfid, servicer_userid, sort_order
        FROM cservice_kf_servicer
        WHERE enabled = 1
        """
    )
    op.execute("DROP INDEX IF EXISTS ix_cservice_kf_servicer_user_id")
    op.execute("DROP TABLE cservice_kf_servicer")
    op.execute("ALTER TABLE cservice_kf_servicer_legacy RENAME TO cservice_kf_servicer")
