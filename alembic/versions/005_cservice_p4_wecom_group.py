"""P4: WeCom group (aibot) parallel domain tables (§10 · D-P4-11).

Revision ID: 005_cservice_p4_wecom_group
Revises: 004_cservice_m7_servicer_user_id
Create Date: 2026-07-07
"""

from __future__ import annotations

from alembic import op

revision = "005_cservice_p4_wecom_group"
down_revision = "004_cservice_m7_servicer_user_id"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS cservice_wg_group (
          chatid TEXT PRIMARY KEY,
          ibot_id TEXT NOT NULL,
          display_name TEXT NOT NULL,
          status TEXT NOT NULL DEFAULT 'active',
          created_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_cservice_wg_group_ibot
          ON cservice_wg_group (ibot_id, status)
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS cservice_wg_session (
          id TEXT PRIMARY KEY,
          chatid TEXT NOT NULL REFERENCES cservice_wg_group(chatid),
          status TEXT NOT NULL DEFAULT 'open',
          pending_reply_count INTEGER NOT NULL DEFAULT 0,
          last_activity_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_cservice_wg_session_chatid
          ON cservice_wg_session (chatid, last_activity_at)
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS cservice_wg_message (
          id TEXT PRIMARY KEY,
          session_id TEXT NOT NULL REFERENCES cservice_wg_session(id),
          direction TEXT NOT NULL,
          source_msgid TEXT UNIQUE,
          msg_type TEXT NOT NULL DEFAULT 'text',
          content TEXT,
          sender_userid TEXT,
          sender_type TEXT,
          draft_id TEXT,
          delivery_status TEXT,
          created_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_cservice_wg_message_session
          ON cservice_wg_message (session_id, created_at)
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS cservice_wg_draft (
          id TEXT PRIMARY KEY,
          session_id TEXT NOT NULL REFERENCES cservice_wg_session(id),
          agent_text TEXT NOT NULL,
          status TEXT NOT NULL DEFAULT 'pending',
          version INTEGER NOT NULL DEFAULT 1,
          superseded_reason TEXT,
          created_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_cservice_wg_draft_session
          ON cservice_wg_draft (session_id, status)
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS cservice_wg_audit_log (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          actor_user_id TEXT,
          chatid TEXT,
          session_id TEXT,
          action TEXT NOT NULL,
          draft_id TEXT,
          edited_text TEXT,
          created_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS cservice_wg_agent_thread (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          ibot_id TEXT NOT NULL,
          chatid TEXT NOT NULL REFERENCES cservice_wg_group(chatid),
          hermes_profile TEXT NOT NULL DEFAULT 'cservice-group-assistant',
          uplink_pending INTEGER NOT NULL DEFAULT 0,
          uplink_started_at TEXT,
          created_at TEXT NOT NULL DEFAULT (datetime('now')),
          UNIQUE (ibot_id, chatid)
        )
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS cservice_wg_reply_anchor (
          chatid TEXT PRIMARY KEY REFERENCES cservice_wg_group(chatid),
          response_url TEXT NOT NULL,
          expires_at TEXT NOT NULL,
          source_msgid TEXT NOT NULL,
          updated_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS cservice_wg_ingress_dedup (
          dedup_key TEXT PRIMARY KEY,
          processed_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS cservice_wg_ingress_dedup")
    op.execute("DROP TABLE IF EXISTS cservice_wg_reply_anchor")
    op.execute("DROP TABLE IF EXISTS cservice_wg_agent_thread")
    op.execute("DROP TABLE IF EXISTS cservice_wg_audit_log")
    op.execute("DROP TABLE IF EXISTS cservice_wg_draft")
    op.execute("DROP TABLE IF EXISTS cservice_wg_message")
    op.execute("DROP TABLE IF EXISTS cservice_wg_session")
    op.execute("DROP TABLE IF EXISTS cservice_wg_group")
