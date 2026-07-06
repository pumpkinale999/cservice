"""CS-21: empty external_userid and system events do not create customers/sessions."""

from __future__ import annotations

from app.db import get_session_factory
from app.models import Customer, EventLog, Session as CSession
from app.services.sync_pipeline import run_sync_for_kf
from tests.conftest import build_mock_wecom_client


def test_empty_external_userid_skips_customer(loaded_seed, wecom_env):
    sync_payload = {
        "errcode": 0,
        "has_more": 0,
        "next_cursor": "c1",
        "msg_list": [
            {
                "msgid": "msg_empty_user",
                "open_kfid": "wkTEST_MINIMAL",
                "external_userid": "",
                "origin": 3,
                "msgtype": "text",
                "send_time": 1,
                "text": {"content": "hello"},
            }
        ],
    }
    client = build_mock_wecom_client(sync_responses=[sync_payload])
    factory = get_session_factory()
    db = factory()
    try:
        before_customers = db.query(Customer).count()
        before_sessions = db.query(CSession).count()
        run_sync_for_kf(db, "wkTEST_MINIMAL", token="T1", client=client)
        assert db.query(Customer).count() == before_customers
        assert db.query(CSession).count() == before_sessions
        events = db.query(EventLog).all()
        assert len(events) == 1
        assert events[0].event_type == "invalid_external_userid"
    finally:
        db.close()


def test_enter_session_logged_not_persisted(loaded_seed, wecom_env):
    sync_payload = {
        "errcode": 0,
        "has_more": 0,
        "next_cursor": "c2",
        "msg_list": [
            {
                "msgid": "evt_enter",
                "open_kfid": "wkTEST_MINIMAL",
                "external_userid": "",
                "event_type": "enter_session",
                "send_time": 2,
            }
        ],
    }
    client = build_mock_wecom_client(sync_responses=[sync_payload])
    factory = get_session_factory()
    db = factory()
    try:
        run_sync_for_kf(db, "wkTEST_MINIMAL", token="T1", client=client)
        assert db.query(Customer).count() == 0
        event = db.query(EventLog).filter_by(event_type="enter_session").one()
        assert event.open_kfid == "wkTEST_MINIMAL"
    finally:
        db.close()
