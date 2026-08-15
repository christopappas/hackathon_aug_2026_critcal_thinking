from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app import config, store
from app.main import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def offline_mode(monkeypatch):
    """Force stub mode so tests never depend on network access or a real token."""
    monkeypatch.setattr(config, "GITHUB_TOKEN", "")


def new_session() -> str:
    return client.post("/session", json={}).json()["session_id"]


def test_hint_unknown_session_returns_404():
    resp = client.post("/hint", json={"session_id": "does-not-exist", "anchor": None})
    assert resp.status_code == 404


def test_hints_climb_one_level_at_a_time_then_cap():
    sid = new_session()
    levels = []
    for _ in range(config.MAX_HINTS_PER_TURN):
        resp = client.post("/hint", json={"session_id": sid, "anchor": None})
        assert resp.status_code == 200
        body = resp.json()
        levels.append(body["hint_level"])
        assert body["hints_used_this_turn"] == body["hint_level"]
        assert body["max_hints_per_turn"] == config.MAX_HINTS_PER_TURN
        assert body["hint"]

    assert levels == list(range(1, config.MAX_HINTS_PER_TURN + 1))

    over_cap = client.post("/hint", json={"session_id": sid, "anchor": None})
    assert over_cap.status_code == 409


def test_sending_a_message_records_hints_used_and_resets_the_budget():
    sid = new_session()
    client.post("/hint", json={"session_id": sid, "anchor": None})
    client.post("/hint", json={"session_id": sid, "anchor": None})

    chat = client.post("/chat", json={"session_id": sid, "message": "Why does this happen?"})
    assert chat.status_code == 200

    session = store.get(sid)
    assert session.exchanges[-1].hints_used == 2
    assert session.pending_hints == 0

    next_hint = client.post("/hint", json={"session_id": sid, "anchor": None})
    assert next_hint.json()["hint_level"] == 1


def test_hints_are_blocked_once_the_conversation_is_complete():
    sid = new_session()
    reply = None
    for _ in range(config.MAX_TURNS):
        reply = client.post(
            "/chat",
            json={"session_id": sid, "message": "Why does this happen and what else could explain it?"},
        ).json()
    assert reply["is_complete"] is True

    resp = client.post("/hint", json={"session_id": sid, "anchor": None})
    assert resp.status_code == 409
