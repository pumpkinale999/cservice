"""cservice ORM entities — aligned with alembic/versions/001_cservice_mvp.py (§13)."""

from __future__ import annotations

from sqlalchemy import ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class KfAccount(Base):
    __tablename__ = "cservice_kf_account"

    open_kfid: Mapped[str] = mapped_column(String(64), primary_key=True)
    display_name: Mapped[str] = mapped_column(Text, nullable=False)
    api_managed: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    last_assigned_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    servicers: Mapped[list[KfServicer]] = relationship("KfServicer", back_populates="account")
    scene_routes: Mapped[list[SceneRoute]] = relationship("SceneRoute", back_populates="account")
    sessions: Mapped[list[Session]] = relationship("Session", back_populates="account")


class KfServicer(Base):
    __tablename__ = "cservice_kf_servicer"

    open_kfid: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("cservice_kf_account.open_kfid"),
        primary_key=True,
    )
    servicer_userid: Mapped[str] = mapped_column(String(64), primary_key=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    account: Mapped[KfAccount] = relationship("KfAccount", back_populates="servicers")


class SceneRoute(Base):
    __tablename__ = "cservice_scene_route"

    open_kfid: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("cservice_kf_account.open_kfid"),
        primary_key=True,
    )
    scene: Mapped[str] = mapped_column(String(128), primary_key=True)
    servicer_userid: Mapped[str] = mapped_column(String(64), nullable=False)

    account: Mapped[KfAccount] = relationship("KfAccount", back_populates="scene_routes")


class Customer(Base):
    __tablename__ = "cservice_customer"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    external_userid: Mapped[str] = mapped_column(String(64), nullable=False)
    display_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    first_scene: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_scene: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[str] = mapped_column(Text, nullable=False)

    sessions: Mapped[list[Session]] = relationship("Session", back_populates="customer")

    __table_args__ = (
        UniqueConstraint("external_userid", name="ix_cservice_customer_external_userid"),
    )


class Session(Base):
    __tablename__ = "cservice_session"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    open_kfid: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("cservice_kf_account.open_kfid"),
        nullable=False,
    )
    customer_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("cservice_customer.id"),
        nullable=False,
    )
    servicer_userid: Mapped[str | None] = mapped_column(String(64), nullable=True)
    status: Mapped[str] = mapped_column(Text, nullable=False, default="open")
    pending_reply_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_activity_at: Mapped[str] = mapped_column(Text, nullable=False)

    account: Mapped[KfAccount] = relationship("KfAccount", back_populates="sessions")
    customer: Mapped[Customer] = relationship("Customer", back_populates="sessions")
    messages: Mapped[list[Message]] = relationship("Message", back_populates="session")
    drafts: Mapped[list[Draft]] = relationship("Draft", back_populates="session")
    agent_thread: Mapped[AgentThread | None] = relationship(
        "AgentThread",
        back_populates="session",
        uselist=False,
    )


class AgentThread(Base):
    __tablename__ = "cservice_agent_thread"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("cservice_session.id"),
        nullable=False,
        unique=True,
    )
    open_kfid: Mapped[str] = mapped_column(String(64), nullable=False)
    external_userid: Mapped[str] = mapped_column(String(64), nullable=False)
    hermes_profile: Mapped[str] = mapped_column(Text, nullable=False, default="cservice-assistant")
    created_at: Mapped[str] = mapped_column(Text, nullable=False)

    session: Mapped[Session] = relationship("Session", back_populates="agent_thread")


class Message(Base):
    __tablename__ = "cservice_message"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    session_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("cservice_session.id"),
        nullable=False,
    )
    direction: Mapped[str] = mapped_column(Text, nullable=False)
    wx_msgid: Mapped[str | None] = mapped_column(String(128), unique=True, nullable=True)
    msg_type: Mapped[str] = mapped_column(Text, nullable=False)
    content: Mapped[str | None] = mapped_column(Text, nullable=True)
    sender_type: Mapped[str | None] = mapped_column(Text, nullable=True)
    draft_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    delivery_status: Mapped[str | None] = mapped_column(Text, nullable=True)
    wx_fail_type: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[str] = mapped_column(Text, nullable=False)

    session: Mapped[Session] = relationship("Session", back_populates="messages")


class Draft(Base):
    __tablename__ = "cservice_draft"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    session_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("cservice_session.id"),
        nullable=False,
    )
    agent_text: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False, default="pending")
    superseded_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[str] = mapped_column(Text, nullable=False)

    session: Mapped[Session] = relationship("Session", back_populates="drafts")


class AuditLog(Base):
    __tablename__ = "cservice_audit_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    actor_user_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    action: Mapped[str] = mapped_column(Text, nullable=False)
    draft_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    edited_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[str] = mapped_column(Text, nullable=False)


class SyncState(Base):
    __tablename__ = "cservice_sync_state"

    open_kfid: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("cservice_kf_account.open_kfid"),
        primary_key=True,
    )
    cursor: Mapped[str | None] = mapped_column(Text, nullable=True)
    updated_at: Mapped[str] = mapped_column(Text, nullable=False)


class WebhookDedup(Base):
    __tablename__ = "cservice_webhook_dedup"

    dedup_key: Mapped[str] = mapped_column(String(256), primary_key=True)
    processed_at: Mapped[str] = mapped_column(Text, nullable=False)


class AssignRetry(Base):
    __tablename__ = "cservice_assign_retry"

    session_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("cservice_session.id"),
        primary_key=True,
    )
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    next_retry_at: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_errcode: Mapped[int | None] = mapped_column(Integer, nullable=True)


class UplinkRetry(Base):
    __tablename__ = "cservice_uplink_retry"

    session_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("cservice_session.id"),
        primary_key=True,
    )
    thread_id: Mapped[int] = mapped_column(Integer, nullable=False)
    trigger_wx_msgid: Mapped[str] = mapped_column(Text, nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    open_kfid: Mapped[str] = mapped_column(String(64), nullable=False)
    external_userid: Mapped[str] = mapped_column(String(64), nullable=False)
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    next_retry_at: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
