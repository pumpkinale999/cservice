"""MVP cservice tables (skstudio docs/cservice-产品设计.md §13 · §28).

Revision ID: 001_cservice_mvp
Revises:
Create Date: 2026-07-05
"""

from __future__ import annotations

from alembic import op

revision = "001_cservice_mvp"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS cservice_kf_account (
          open_kfid TEXT PRIMARY KEY,
          display_name TEXT NOT NULL,
          api_managed INTEGER NOT NULL DEFAULT 1,
          last_assigned_index INTEGER NOT NULL DEFAULT 0
        )
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS cservice_kf_servicer (
          open_kfid TEXT NOT NULL REFERENCES cservice_kf_account(open_kfid),
          servicer_userid TEXT NOT NULL,
          sort_order INTEGER NOT NULL DEFAULT 0,
          PRIMARY KEY (open_kfid, servicer_userid)
        )
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS cservice_scene_route (
          open_kfid TEXT NOT NULL REFERENCES cservice_kf_account(open_kfid),
          scene TEXT NOT NULL,
          servicer_userid TEXT NOT NULL,
          PRIMARY KEY (open_kfid, scene)
        )
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS cservice_customer (
          id TEXT PRIMARY KEY,
          external_userid TEXT NOT NULL,
          display_name TEXT,
          first_scene TEXT,
          last_scene TEXT,
          created_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
        """
    )
    op.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS ix_cservice_customer_external_userid
          ON cservice_customer (external_userid)
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS cservice_session (
          id TEXT PRIMARY KEY,
          open_kfid TEXT NOT NULL REFERENCES cservice_kf_account(open_kfid),
          customer_id TEXT NOT NULL REFERENCES cservice_customer(id),
          servicer_userid TEXT,
          status TEXT NOT NULL DEFAULT 'open',
          pending_reply_count INTEGER NOT NULL DEFAULT 0,
          last_activity_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_cservice_session_servicer
          ON cservice_session (servicer_userid, last_activity_at)
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_cservice_session_kf_customer
          ON cservice_session (open_kfid, customer_id)
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS cservice_agent_thread (
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
        CREATE TABLE IF NOT EXISTS cservice_message (
          id TEXT PRIMARY KEY,
          session_id TEXT NOT NULL REFERENCES cservice_session(id),
          direction TEXT NOT NULL,
          wx_msgid TEXT UNIQUE,
          msg_type TEXT NOT NULL,
          content TEXT,
          sender_type TEXT,
          draft_id TEXT,
          delivery_status TEXT,
          wx_fail_type INTEGER,
          created_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS cservice_draft (
          id TEXT PRIMARY KEY,
          session_id TEXT NOT NULL REFERENCES cservice_session(id),
          agent_text TEXT NOT NULL,
          status TEXT NOT NULL DEFAULT 'pending',
          superseded_reason TEXT,
          created_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS cservice_audit_log (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          actor_user_id TEXT,
          action TEXT NOT NULL,
          draft_id TEXT,
          edited_text TEXT,
          created_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS cservice_sync_state (
          open_kfid TEXT PRIMARY KEY REFERENCES cservice_kf_account(open_kfid),
          cursor TEXT,
          updated_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS cservice_webhook_dedup (
          dedup_key TEXT PRIMARY KEY,
          processed_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS cservice_assign_retry (
          session_id TEXT PRIMARY KEY REFERENCES cservice_session(id),
          attempts INTEGER NOT NULL DEFAULT 0,
          next_retry_at TEXT,
          last_errcode INTEGER
        )
        """
    )


def downgrade() -> None:
    for table in (
        "cservice_assign_retry",
        "cservice_webhook_dedup",
        "cservice_sync_state",
        "cservice_audit_log",
        "cservice_draft",
        "cservice_message",
        "cservice_agent_thread",
        "cservice_session",
        "cservice_customer",
        "cservice_scene_route",
        "cservice_kf_servicer",
        "cservice_kf_account",
    ):
        op.execute(f"DROP TABLE IF EXISTS {table}")
