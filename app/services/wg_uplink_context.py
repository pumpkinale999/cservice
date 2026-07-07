"""Rich Hermes group uplink body builder (§6.3 · CS-34)."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.models import WgGroup, WgMessage, WgSession

_MAX_RECENT = 10
_MAX_LINE_CHARS = 500
_MAX_BODY_CHARS = 4000
_BOT_DISPLAY_NAME = "数坤坤健康助手"

_DRAFT_REQUIREMENTS = (
    "【起草要求】\n"
    "- 只回复「本轮待回复」\n"
    "- 对外客户一律称呼「您」（不用「你」）\n"
    "- 输出可直接发送的正文，无前后缀"
)


def _truncate(text: str, limit: int) -> str:
    text = (text or "").strip()
    if len(text) <= limit:
        return text
    return text[: limit - 1] + "…"


def sender_display_name(sender_userid: str | None) -> str:
    uid = (sender_userid or "").strip()
    if not uid:
        return "成员"
    suffix = uid[-4:] if len(uid) > 4 else uid
    return f"用户·{suffix}"


def _format_line(msg: WgMessage) -> str | None:
    if msg.msg_type != "text":
        return None
    if msg.direction == "outbound" and msg.delivery_status == "draft_only":
        return None
    content = _truncate(msg.content or "", _MAX_LINE_CHARS)
    if not content:
        return None
    if msg.direction == "inbound":
        name = sender_display_name(msg.sender_userid)
        return f"{name}：{content}"
    if msg.sender_type == "agent":
        return f"{_BOT_DISPLAY_NAME}：{content}"
    return f"接待：{content}"


def collect_pending_inbound_lines(db: Session, session_id: str) -> list[str]:
    """Inbound text since last outbound in current reply round."""
    messages = (
        db.query(WgMessage)
        .filter_by(session_id=session_id)
        .order_by(WgMessage.created_at.asc())
        .all()
    )
    last_out_idx = -1
    for idx, msg in enumerate(messages):
        if msg.direction == "outbound" and msg.delivery_status == "sent":
            last_out_idx = idx
    pending = messages[last_out_idx + 1 :]
    lines: list[str] = []
    for msg in pending:
        if msg.direction != "inbound" or msg.msg_type != "text":
            continue
        name = sender_display_name(msg.sender_userid)
        content = _truncate(msg.content or "", _MAX_LINE_CHARS)
        if content:
            lines.append(f"{name}：{content}")
    return lines


def build_wg_uplink_body(
    db: Session,
    *,
    session: WgSession,
    group: WgGroup,
    pending_lines: list[str] | None = None,
    latest_sender_userid: str | None = None,
) -> str:
    lines = pending_lines if pending_lines is not None else collect_pending_inbound_lines(
        db, session.id
    )
    sender_name = sender_display_name(latest_sender_userid)
    if not lines and latest_sender_userid:
        lines = [f"{sender_name}：（无文本）"]

    messages = (
        db.query(WgMessage)
        .filter_by(session_id=session.id)
        .order_by(WgMessage.created_at.asc())
        .all()
    )
    recent_lines: list[str] = []
    for msg in messages:
        line = _format_line(msg)
        if line:
            recent_lines.append(line)
    recent_lines = recent_lines[-_MAX_RECENT:]

    parts = [
        f"【群名称】{group.display_name}",
        f"【智能机器人】{_BOT_DISPLAY_NAME}",
        f"【发送者】{sender_name}",
        "",
        "【近期对话】",
    ]
    if recent_lines:
        parts.extend(recent_lines)
    else:
        parts.append("（无）")
    parts.extend(["", "【本轮待回复】"])
    if lines:
        parts.extend(lines)
    else:
        parts.append("（无）")
    parts.extend(["", _DRAFT_REQUIREMENTS])
    body = "\n".join(parts)
    if len(body) > _MAX_BODY_CHARS:
        body = body[: _MAX_BODY_CHARS - 1] + "…"
    return body
