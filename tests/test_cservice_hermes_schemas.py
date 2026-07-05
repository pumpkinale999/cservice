"""Hermes schema tests (M3 · PR-1)."""

from __future__ import annotations

from app.hermes.schemas import (
    CserviceCustomerUplink,
    CserviceDraftReply,
    GatewayRegister,
    parse_business_frame,
)
from tests.conftest import load_json_fixture


def test_gateway_register_parse():
    reg = GatewayRegister.from_dict(
        {
            "type": "gateway_register",
            "gateway_role": "cservice",
            "agent_slug": "cservice-assistant",
        }
    )
    assert reg is not None
    assert reg.gateway_role == "cservice"


def test_gateway_register_rejects_master():
    assert GatewayRegister.from_dict({"type": "gateway_register", "gateway_role": "master"}) is None


def test_customer_uplink_roundtrip():
    raw = load_json_fixture("cservice_customer_uplink.json")
    uplink = CserviceCustomerUplink.from_dict(raw)
    assert uplink is not None
    assert uplink.to_dict()["type"] == "cservice_customer_uplink"
    assert uplink.trigger_wx_msgid == "msg_inbound_001"


def test_customer_uplink_missing_fields():
    assert CserviceCustomerUplink.from_dict({"type": "cservice_customer_uplink"}) is None


def test_draft_reply_parse():
    raw = load_json_fixture("draft_reply_downlink.json")
    reply = CserviceDraftReply.from_dict(raw)
    assert reply is not None
    assert reply.stream_status == "final"


def test_parse_business_frame():
    raw = load_json_fixture("draft_reply_downlink.json")
    assert parse_business_frame(raw) is not None
