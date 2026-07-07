"""WSS frame schemas (§22.3 · P4 §13)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal


@dataclass(frozen=True)
class GatewayRegister:
    gateway_role: str
    agent_slug: str
    protocol_version: int = 1

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> GatewayRegister | None:
        if data.get("type") != "gateway_register":
            return None
        role = str(data.get("gateway_role", "")).strip()
        slug = str(data.get("agent_slug", "")).strip()
        if role not in ("cservice", "cservice-group") or not slug:
            return None
        return cls(
            gateway_role=role,
            agent_slug=slug,
            protocol_version=int(data.get("protocol_version", 1)),
        )


@dataclass(frozen=True)
class CserviceCustomerUplink:
    thread_id: int
    session_id: str
    open_kfid: str
    external_userid: str
    body: str
    trigger_wx_msgid: str
    protocol_version: int = 1

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": "cservice_customer_uplink",
            "protocol_version": self.protocol_version,
            "thread_id": self.thread_id,
            "session_id": self.session_id,
            "open_kfid": self.open_kfid,
            "external_userid": self.external_userid,
            "body": self.body,
            "trigger_wx_msgid": self.trigger_wx_msgid,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CserviceCustomerUplink | None:
        if data.get("type") != "cservice_customer_uplink":
            return None
        try:
            thread_id = int(data["thread_id"])
        except (KeyError, TypeError, ValueError):
            return None
        session_id = str(data.get("session_id", "")).strip()
        open_kfid = str(data.get("open_kfid", "")).strip()
        external_userid = str(data.get("external_userid", "")).strip()
        body = str(data.get("body", ""))
        trigger_wx_msgid = str(data.get("trigger_wx_msgid", "")).strip()
        if not session_id or not trigger_wx_msgid:
            return None
        return cls(
            thread_id=thread_id,
            session_id=session_id,
            open_kfid=open_kfid,
            external_userid=external_userid,
            body=body,
            trigger_wx_msgid=trigger_wx_msgid,
            protocol_version=int(data.get("protocol_version", 1)),
        )


@dataclass(frozen=True)
class CserviceGroupUplink:
    thread_id: int
    session_id: str
    ibot_id: str
    chatid: str
    body: str
    trigger_source_msgid: str
    protocol_version: int = 1

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": "cservice_group_uplink",
            "protocol_version": self.protocol_version,
            "thread_id": self.thread_id,
            "session_id": self.session_id,
            "ibot_id": self.ibot_id,
            "chatid": self.chatid,
            "body": self.body,
            "trigger_source_msgid": self.trigger_source_msgid,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CserviceGroupUplink | None:
        if data.get("type") != "cservice_group_uplink":
            return None
        try:
            thread_id = int(data["thread_id"])
        except (KeyError, TypeError, ValueError):
            return None
        session_id = str(data.get("session_id", "")).strip()
        ibot_id = str(data.get("ibot_id", "")).strip()
        chatid = str(data.get("chatid", "")).strip()
        body = str(data.get("body", ""))
        trigger = str(
            data.get("trigger_source_msgid") or data.get("trigger_wx_msgid") or ""
        ).strip()
        if not session_id or not trigger or not chatid:
            return None
        return cls(
            thread_id=thread_id,
            session_id=session_id,
            ibot_id=ibot_id,
            chatid=chatid,
            body=body,
            trigger_source_msgid=trigger,
            protocol_version=int(data.get("protocol_version", 1)),
        )


@dataclass(frozen=True)
class CserviceDraftReply:
    thread_id: int
    session_id: str
    body: str
    stream_status: Literal["final", "failed"]
    trigger_wx_msgid: str | None = None
    trigger_source_msgid: str | None = None
    protocol_version: int = 1

    @property
    def trigger_id(self) -> str | None:
        return self.trigger_source_msgid or self.trigger_wx_msgid

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CserviceDraftReply | None:
        if data.get("type") != "cservice_draft_reply":
            return None
        try:
            thread_id = int(data["thread_id"])
        except (KeyError, TypeError, ValueError):
            return None
        session_id = str(data.get("session_id", "")).strip()
        body = str(data.get("body", ""))
        stream_status = str(data.get("stream_status", "final")).strip()
        if stream_status not in ("final", "failed"):
            return None
        if not session_id:
            return None
        trigger_wx = data.get("trigger_wx_msgid")
        trigger_src = data.get("trigger_source_msgid")
        trigger_wx_msgid = str(trigger_wx).strip() if trigger_wx else None
        trigger_source_msgid = str(trigger_src).strip() if trigger_src else None
        return cls(
            thread_id=thread_id,
            session_id=session_id,
            body=body,
            stream_status=stream_status,  # type: ignore[arg-type]
            trigger_wx_msgid=trigger_wx_msgid,
            trigger_source_msgid=trigger_source_msgid,
            protocol_version=int(data.get("protocol_version", 1)),
        )


def parse_business_frame(data: dict[str, Any]) -> CserviceDraftReply | None:
    return CserviceDraftReply.from_dict(data)
