"""Session access control for BFF actor (§14)."""

from __future__ import annotations

from fastapi import HTTPException, status

from app.models import Session as CSession


def require_session_servicer(session: CSession, actor_userid: str) -> None:
    """Raise 403 if actor is not the assigned servicer."""
    servicer = (session.servicer_userid or "").strip()
    actor = actor_userid.strip()
    if not servicer or servicer != actor:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="not_session_servicer",
        )


def require_session_open(session: CSession) -> None:
    """Raise 409 if session is closed (§8.2)."""
    if session.status == "closed":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="session_closed",
        )
