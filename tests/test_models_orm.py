"""ORM CRUD smoke tests (M1 · PR-1)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import Customer, KfAccount, KfServicer, Message, Session as CSession


def _now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def test_kf_account_and_servicer_crud(tmp_cservice_db):
    from app.db import get_session_factory

    factory = get_session_factory()
    db: Session = factory()
    try:
        account = KfAccount(
            open_kfid="wkTEST001",
            display_name="售前",
            api_managed=1,
            last_assigned_index=0,
        )
        db.add(account)
        db.add(
            KfServicer(
                open_kfid="wkTEST001",
                servicer_userid="zhangsan",
                sort_order=0,
            )
        )
        db.commit()

        row = db.query(KfServicer).filter_by(open_kfid="wkTEST001").one()
        assert row.servicer_userid == "zhangsan"
        assert row.account.display_name == "售前"
    finally:
        db.close()


def test_customer_session_message_chain(tmp_cservice_db):
    from app.db import get_session_factory

    factory = get_session_factory()
    db: Session = factory()
    try:
        db.add(
            KfAccount(
                open_kfid="wkTEST002",
                display_name="售后",
                api_managed=1,
                last_assigned_index=0,
            )
        )
        customer_id = str(uuid.uuid4())
        session_id = str(uuid.uuid4())
        db.add(
            Customer(
                id=customer_id,
                external_userid="wmTEST001",
                display_name="张三",
                created_at=_now(),
            )
        )
        db.add(
            CSession(
                id=session_id,
                open_kfid="wkTEST002",
                customer_id=customer_id,
                servicer_userid="zhangsan",
                status="open",
                pending_reply_count=1,
                last_activity_at=_now(),
            )
        )
        db.add(
            Message(
                id=str(uuid.uuid4()),
                session_id=session_id,
                direction="inbound",
                wx_msgid="msgid_unique_001",
                msg_type="text",
                content="你好",
                sender_type="customer",
                created_at=_now(),
            )
        )
        db.commit()

        msg = db.query(Message).filter_by(wx_msgid="msgid_unique_001").one()
        assert msg.content == "你好"
        assert msg.session.servicer_userid == "zhangsan"
    finally:
        db.close()


def test_wx_msgid_unique_constraint(tmp_cservice_db):
    from app.db import get_session_factory

    factory = get_session_factory()
    db: Session = factory()
    try:
        db.add(
            KfAccount(
                open_kfid="wkTEST003",
                display_name="测试",
                api_managed=1,
                last_assigned_index=0,
            )
        )
        customer_id = str(uuid.uuid4())
        session_id = str(uuid.uuid4())
        db.add(
            Customer(
                id=customer_id,
                external_userid="wmTEST002",
                created_at=_now(),
            )
        )
        db.add(
            CSession(
                id=session_id,
                open_kfid="wkTEST003",
                customer_id=customer_id,
                status="open",
                pending_reply_count=0,
                last_activity_at=_now(),
            )
        )
        wx_msgid = "msgid_dup_test"
        db.add(
            Message(
                id=str(uuid.uuid4()),
                session_id=session_id,
                direction="inbound",
                wx_msgid=wx_msgid,
                msg_type="text",
                content="first",
                created_at=_now(),
            )
        )
        db.commit()

        db.add(
            Message(
                id=str(uuid.uuid4()),
                session_id=session_id,
                direction="inbound",
                wx_msgid=wx_msgid,
                msg_type="text",
                content="duplicate",
                created_at=_now(),
            )
        )
        with pytest.raises(IntegrityError):
            db.commit()
    finally:
        db.rollback()
        db.close()
