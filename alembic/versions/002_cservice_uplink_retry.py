"""Add cservice_uplink_retry (M3 · §15.5).

Revision ID: 002_cservice_uplink_retry
Revises: 001_cservice_mvp
Create Date: 2026-07-05
"""

from __future__ import annotations

from alembic import op

revision = "002_cservice_uplink_retry"
down_revision = "001_cservice_mvp"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS cservice_uplink_retry (
          session_id TEXT PRIMARY KEY REFERENCES cservice_session(id),
          thread_id INTEGER NOT NULL,
          trigger_wx_msgid TEXT NOT NULL,
          body TEXT NOT NULL,
          open_kfid TEXT NOT NULL,
          external_userid TEXT NOT NULL,
          attempts INTEGER NOT NULL DEFAULT 0,
          next_retry_at TEXT,
          last_error TEXT
        )
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS cservice_uplink_retry")
