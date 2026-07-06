"""Rich Hermes uplink body builder (§5.4 · §22.3 · CS-19)."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.models import KfAccount, Message, Session as CSession

_MAX_RECENT = 10
_MAX_LINE_CHARS = 500
_MAX_BODY_CHARS = 4000

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


def _format_line(msg: Message) -> str | None:
    if msg.msg_type != "text":
        return None
    if msg.direction == "outbound" and msg.delivery_status == "draft_only":
        return None
    content = _truncate(msg.content or "", _MAX_LINE_CHARS)
    if not content:
        return None
    if msg.direction == "inbound":
        return f"客户：{content}"
    if msg.sender_type == "agent":
        return f"客服助手：{content}"
    return f"接待：{content}"


def build_uplink_body(
    db: Session,
    *,
    csession: CSession,
    external_userid: str,
    pending_reply_text: str,
    scene: str | None = None,
) -> str:
    account = db.get(KfAccount, csession.open_kfid)
    account_name = account.display_name if account else csession.open_kfid
    customer_name = csession.customer.display_name if csession.customer else external_userid

    messages = (
        db.query(Message)
        .filter_by(session_id=csession.id)
        .order_by(Message.created_at.asc())
        .all()
    )
    recent_lines: list[str] = []
    for msg in messages:
        line = _format_line(msg)
        if line:
            recent_lines.append(line)
    recent_lines = recent_lines[-_MAX_RECENT:]

    parts = [
        f"【客服账号】{account_name}",
        f"【客户】{customer_name}",
        f"【场景】{scene or '无'}",
        "",
        "【近期对话】",
    ]
    if recent_lines:
        parts.extend(recent_lines)
    else:
        parts.append("（无）")
    parts.extend(
        [
            "",
            "【本轮待回复】",
            f"客户：{_truncate(pending_reply_text, _MAX_LINE_CHARS)}",
            "",
            _DRAFT_REQUIREMENTS,
        ]
    )
    body = "\n".join(parts)
    if len(body) > _MAX_BODY_CHARS:
        body = body[: _MAX_BODY_CHARS - 1] + "…"
    return body
