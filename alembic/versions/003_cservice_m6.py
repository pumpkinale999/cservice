"""M6 schema: thread reuse, uplink_pending, draft version, event_log (§28.4.1).

Revision ID: 003_cservice_m6
Revises: 002_cservice_uplink_retry
Create Date: 2026-07-06
"""

from __future__ import annotations

from alembic import op

revision = "003_cservice_m6"
down_revision = "002_cservice_uplink_retry"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Recreate agent_thread: UNIQUE(open_kfid, external_userid) instead of UNIQUE(session_id)
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS cservice_agent_thread_m6 (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          session_id TEXT NOT NULL REFERENCES cservice_session(id),
          open_kfid TEXT NOT NULL,
          external_userid TEXT NOT NULL,
          hermes_profile TEXT NOT NULL DEFAULT 'cservice-assistant',
          uplink_pending INTEGER NOT NULL DEFAULT 0,
          uplink_started_at TEXT,
          created_at TEXT NOT NULL DEFAULT (datetime('now')),
          UNIQUE(open_kfid, external_userid)
        )
        """
    )
    op.execute(
        """
        INSERT INTO cservice_agent_thread_m6
          (id, session_id, open_kfid, external_userid, hermes_profile, created_at)
        SELECT t.id, t.session_id, t.open_kfid, t.external_userid, t.hermes_profile, t.created_at
        FROM cservice_agent_thread t
        INNER JOIN (
          SELECT open_kfid, external_userid, MAX(id) AS keep_id
          FROM cservice_agent_thread
          GROUP BY open_kfid, external_userid
        ) d ON t.id = d.keep_id
        """
    )
    op.execute("DROP TABLE IF EXISTS cservice_agent_thread")
    op.execute("ALTER TABLE cservice_agent_thread_m6 RENAME TO cservice_agent_thread")

    op.execute(
        """
        ALTER TABLE cservice_draft
        ADD COLUMN version INTEGER NOT NULL DEFAULT 1
        """
    )

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS cservice_event_log (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          open_kfid TEXT,
          event_type TEXT NOT NULL,
          external_userid TEXT,
          payload_json TEXT,
          created_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS cservice_event_log")
    # draft.version: SQLite cannot DROP COLUMN easily; leave for downgrade simplicity
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS cservice_agent_thread_legacy (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          session_id TEXT NOT NULL UNIQUE REFERENCES cservice_session(id),
          open_kfid TEXT NOT NULL,
          external_userid TEXT NOT NULL,
          hermes_profile TEXT NOT NULL DEFAULT 'cservice-assistant',
          created_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
        """
    )
    op.execute(
        """
        INSERT INTO cservice_agent_thread_legacy
          (id, session_id, open_kfid, external_userid, hermes_profile, created_at)
        SELECT id, session_id, open_kfid, external_userid, hermes_profile, created_at
        FROM cservice_agent_thread
        """
    )
    op.execute("DROP TABLE IF EXISTS cservice_agent_thread")
    op.execute("ALTER TABLE cservice_agent_thread_legacy RENAME TO cservice_agent_thread")
