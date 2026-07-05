"""Badge / pending_reply_count helpers (§13.3)."""

from __future__ import annotations

from app.models import Session as CSession


def on_text_inbound(session: CSession) -> None:
    """New reply round: 0→1; same round: unchanged."""
    if session.pending_reply_count == 0:
        session.pending_reply_count = 1


def on_round_cover_outbound(session: CSession) -> None:
    session.pending_reply_count = 0


def on_send_fail_rollback(session: CSession) -> None:
    """Restore badge when async send fails after we decremented (§23.2)."""
    if session.pending_reply_count == 0:
        session.pending_reply_count = 1


def fail_type_label(fail_type: int) -> str:
    """Map WeCom fail_type to UI copy (§23.2)."""
    mapping = {
        4: "超过 48 小时，无法送达",
        6: "超过本轮 5 条限制",
        10: "用户拒收",
    }
    return mapping.get(fail_type, f"发送失败（code {fail_type}）")
