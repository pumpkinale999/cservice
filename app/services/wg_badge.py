"""Badge / pending_reply_count helpers for WeCom group sessions (§13.3)."""

from __future__ import annotations

from app.models import WgSession


def on_text_inbound(session: WgSession) -> None:
    """New reply round: 0→1; same round: unchanged."""
    if session.pending_reply_count == 0:
        session.pending_reply_count = 1


def on_round_cover_outbound(session: WgSession) -> None:
    session.pending_reply_count = 0
