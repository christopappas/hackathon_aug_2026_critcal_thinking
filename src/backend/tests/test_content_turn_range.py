from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app import config
from app.main import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def offline_mode(monkeypatch):
    """Force stub mode so tests never depend on network access or a real token."""
    monkeypatch.setattr(config, "GITHUB_TOKEN", "")


def test_defaults_to_global_config_when_template_has_no_override():
    content = {"id": "no-override"}
    assert config.content_turn_range(content) == (config.MIN_TURNS, config.MAX_TURNS)


def test_template_override_is_used_when_present():
    content = {"id": "shorter", "min_turns": 2, "max_turns": 4}
    assert config.content_turn_range(content) == (2, 4)


def test_partial_override_falls_back_for_the_missing_side():
    content = {"id": "max-only", "max_turns": 4}
    assert config.content_turn_range(content) == (config.MIN_TURNS, 4)


def test_min_turns_below_one_is_rejected():
    with pytest.raises(ValueError, match="min_turns must be at least 1"):
        config.content_turn_range({"id": "bad", "min_turns": 0, "max_turns": 3})


def test_max_turns_below_min_turns_is_rejected():
    with pytest.raises(ValueError, match="less than min_turns"):
        config.content_turn_range({"id": "bad", "min_turns": 4, "max_turns": 2})


def test_max_turns_above_ceiling_is_rejected():
    with pytest.raises(ValueError, match="exceeds the ceiling"):
        config.content_turn_range({"id": "bad", "max_turns": config.MAX_TURNS_CEILING + 1})


def test_max_turns_at_the_ceiling_is_allowed():
    min_turns, max_turns = config.content_turn_range(
        {"id": "edge", "min_turns": 1, "max_turns": config.MAX_TURNS_CEILING}
    )
    assert max_turns == config.MAX_TURNS_CEILING


def test_session_endpoint_reflects_the_template_override():
    resp = client.post("/session", json={"content_id": "study-music"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["min_turns"] == 2
    assert body["max_turns"] == 4


def test_session_endpoint_uses_global_default_without_an_override():
    resp = client.post("/session", json={"content_id": "mars-headline"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["min_turns"] == config.MIN_TURNS
    assert body["max_turns"] == config.MAX_TURNS


def test_the_overridden_session_actually_completes_at_its_own_max_turns():
    session = client.post("/session", json={"content_id": "study-music"}).json()
    sid = session["session_id"]
    reply = None
    for _ in range(4):
        reply = client.post(
            "/chat",
            json={"session_id": sid, "message": "Why does this happen and what else could explain it?"},
        ).json()
    assert reply["turns_used"] == 4
    assert reply["is_complete"] is True

    fifth = client.post("/chat", json={"session_id": sid, "message": "one more"})
    assert fifth.status_code == 409
