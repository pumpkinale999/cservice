"""Customer display_name enrichment tests."""

from __future__ import annotations

from app.db import get_session_factory
from app.models import Customer
from app.services.customer_display import (
    display_name_is_placeholder,
    enrich_customer_display_names,
)
from app.services.sync_pipeline import run_sync_for_kf
from tests.conftest import build_mock_wecom_client, load_json_fixture


def test_display_name_is_placeholder():
    customer = Customer(
        id="c1",
        external_userid="wmABC",
        display_name="wmABC",
        created_at="2026-01-01T00:00:00+00:00",
    )
    assert display_name_is_placeholder(customer) is True
    customer.display_name = "张三"
    assert display_name_is_placeholder(customer) is False


def test_sync_pipeline_sets_customer_nickname(loaded_seed, wecom_env):
    client = build_mock_wecom_client(
        sync_responses=[load_json_fixture("sync_msg_text_inbound.json")]
    )
    factory = get_session_factory()
    db = factory()
    try:
        run_sync_for_kf(db, "wkTEST_MINIMAL", token="T1", client=client)
        customer = db.query(Customer).filter_by(external_userid="wmTEST001").one()
        assert customer.display_name == "测试客户"
        client.customer_batchget.assert_called_once()
    finally:
        db.close()


def test_enrich_skips_manual_display_name(loaded_seed, wecom_env):
    factory = get_session_factory()
    db = factory()
    client = build_mock_wecom_client()
    try:
        customer = Customer(
            id="manual-1",
            external_userid="wmMANUAL",
            display_name="李女士",
            created_at="2026-01-01T00:00:00+00:00",
        )
        db.add(customer)
        db.flush()
        enrich_customer_display_names(db, client, [customer])
        assert customer.display_name == "李女士"
        client.customer_batchget.assert_not_called()
    finally:
        db.close()


def test_enrich_keeps_external_userid_when_api_misses(loaded_seed, wecom_env):
    factory = get_session_factory()
    db = factory()
    client = build_mock_wecom_client(customer_batchget_response={"customer_list": []})
    try:
        customer = Customer(
            id="missing-1",
            external_userid="wmMISSING",
            display_name="wmMISSING",
            created_at="2026-01-01T00:00:00+00:00",
        )
        db.add(customer)
        db.flush()
        enrich_customer_display_names(db, client, [customer])
        assert customer.display_name == "wmMISSING"
    finally:
        db.close()
