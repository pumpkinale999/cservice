"""Uplink draft requirements."""

from __future__ import annotations

from app.services.uplink_context import _DRAFT_REQUIREMENTS


def test_draft_requirements_use_formal_nin():
    assert "称呼「您」" in _DRAFT_REQUIREMENTS
    assert "不用「你」" in _DRAFT_REQUIREMENTS
