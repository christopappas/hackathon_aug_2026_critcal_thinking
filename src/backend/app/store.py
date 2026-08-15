from __future__ import annotations

import uuid

from .models import Session

_SESSIONS: dict[str, Session] = {}


def create(content_id: str, min_turns: int, max_turns: int) -> Session:
    session = Session(
        session_id=uuid.uuid4().hex[:12],
        content_id=content_id,
        min_turns=min_turns,
        max_turns=max_turns,
    )
    _SESSIONS[session.session_id] = session
    return session


def get(session_id: str) -> Session | None:
    return _SESSIONS.get(session_id)


def save(session: Session) -> None:
    _SESSIONS[session.session_id] = session
