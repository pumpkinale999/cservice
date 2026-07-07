"""WeCom error detail mapping tests."""

from __future__ import annotations

import pytest
from fastapi import HTTPException

from app.services.wecom_error_detail import (
    classify_wecom_errcode,
    raise_for_group_send_result,
    raise_for_wecom_error,
)
from app.services.wecom_errors import CserviceWecomError


def test_classify_anchor_consumed():
    assert classify_wecom_errcode(60140) == "anchor_consumed"


def test_classify_no_session():
    assert classify_wecom_errcode(600039) == "wecom_no_session"


def test_raise_for_wecom_error_maps_60140():
    with pytest.raises(HTTPException) as exc:
        raise_for_wecom_error(CserviceWecomError(60140, "invalid response code"))
    assert exc.value.status_code == 502
    assert exc.value.detail["code"] == "anchor_consumed"


def test_raise_for_group_send_gateway_offline():
    with pytest.raises(HTTPException) as exc:
        raise_for_group_send_result({"ok": False, "code": "gateway_offline"})
    assert exc.value.status_code == 503
    assert exc.value.detail["code"] == "gateway_offline"


def test_raise_for_group_send_no_session():
    with pytest.raises(HTTPException) as exc:
        raise_for_group_send_result(
            {"ok": False, "code": "wecom_no_session", "errcode": 600039, "errmsg": "x"}
        )
    assert exc.value.status_code == 502
    assert exc.value.detail["code"] == "wecom_no_session"
