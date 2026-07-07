"""P4-M2: wg uplink retry table (§15.5).

Revision ID: 006_cservice_p4_wg_uplink_retry
Revises: 005_cservice_p4_wecom_group
Create Date: 2026-07-07
"""

from __future__ import annotations

from alembic import op

revision = "006_cservice_p4_wg_uplink_retry"
down_revision = "005_cservice_p4_wecom_group"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS cservice_wg_uplink_retry (
          session_id TEXT PRIMARY KEY REFERENCES cservice_wg_session(id),
          thread_id INTEGER NOT NULL,
          trigger_source_msgid TEXT NOT NULL,
          body TEXT NOT NULL,
          ibot_id TEXT NOT NULL,
          chatid TEXT NOT NULL,
          attempts INTEGER NOT NULL DEFAULT 0,
          next_retry_at TEXT,
          last_error TEXT
        )
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS cservice_wg_uplink_retry")
