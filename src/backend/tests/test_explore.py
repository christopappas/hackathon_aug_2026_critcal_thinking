from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app import config, evaluator, explore, store
from app.main import app
from app.models import Exchange, ExploreMessage, ExploreThread, Session

client = TestClient(app)

CONTENT = {
    "title": "Do Phones Hurt Test Scores?",
    "body": "Our survey of 200 students found a link between screen time and test scores.",
    "chart": {"alt": "A scatter plot of screen time versus test score"},
    "grade_level": 6,
}


@pytest.fixture(autouse=True)
def offline_mode(monkeypatch):
    """Force stub mode so tests never depend on network access or a real token."""
    monkeypatch.setattr(config, "GITHUB_TOKEN", "")


def new_session() -> str:
    return client.post("/session", json={}).json()["session_id"]


# --- explore.py: stub fallback ---------------------------------------------------


def test_stub_opening_names_the_anchor_when_given_one():
    text = explore._stub_opening("the passage about 200 students")
    assert "the passage about 200 students" in text


def test_stub_opening_falls_back_generically_without_an_anchor():
    text = explore._stub_opening(None)
    assert text


def test_generate_opening_falls_back_to_stub_without_a_token(monkeypatch):
    monkeypatch.setattr(config, "GITHUB_TOKEN", "")
    text, used_llm = explore.generate_opening(CONTENT, "the chart")
    assert used_llm is False
    assert text


def test_generate_reply_falls_back_to_stub_without_a_token(monkeypatch):
    monkeypatch.setattr(config, "GITHUB_TOKEN", "")
    thread = ExploreThread(anchor_excerpt="the chart")
    text, used_llm = explore.generate_reply(thread, CONTENT, "Why does that happen?")
    assert used_llm is False
    assert text


def test_stub_reply_cycles_rather_than_repeating_every_time():
    thread = ExploreThread(anchor_excerpt="the chart")
    seen = set()
    for i in range(len(explore._STUB_REPLIES)):
        thread.messages.append(ExploreMessage(student_message="m", llm_response="r"))
        seen.add(explore._stub_reply(thread))
    assert len(seen) == len(explore._STUB_REPLIES)


# --- /explore/start and /explore/message endpoints ---------------------------------


def test_explore_start_unknown_session_returns_404():
    resp = client.post(
        "/explore/start", json={"session_id": "does-not-exist", "anchor": {"kind": "text", "quote": "hi"}}
    )
    assert resp.status_code == 404


def test_explore_message_before_start_returns_409():
    sid = new_session()
    resp = client.post("/explore/message", json={"session_id": sid, "message": "hello"})
    assert resp.status_code == 409


def test_explore_start_then_message_round_trip():
    sid = new_session()
    start = client.post(
        "/explore/start",
        json={"session_id": sid, "anchor": {"kind": "text", "quote": "Our survey of 200 students"}},
    )
    assert start.status_code == 200
    body = start.json()
    assert body["opening"]
    assert body["anchor_excerpt"]
    assert body["max_messages"] == config.MAX_EXPLORE_MESSAGES

    reply = client.post("/explore/message", json={"session_id": sid, "message": "Why 200 students?"})
    assert reply.status_code == 200
    reply_body = reply.json()
    assert reply_body["reply"]
    assert reply_body["messages_used"] == 1
    assert reply_body["max_messages"] == config.MAX_EXPLORE_MESSAGES


def test_starting_a_new_explore_replaces_the_previous_thread():
    sid = new_session()
    client.post("/explore/start", json={"session_id": sid, "anchor": {"kind": "text", "quote": "Our survey"}})
    client.post("/explore/message", json={"session_id": sid, "message": "first thread message"})

    client.post("/explore/start", json={"session_id": sid, "anchor": {"kind": "temporal", "timestamp_s": 9.0}})
    session = store.get(sid)
    assert session.explore.messages == []


def test_explore_message_cap_is_enforced(monkeypatch):
    monkeypatch.setattr(config, "MAX_EXPLORE_MESSAGES", 2)
    sid = new_session()
    client.post("/explore/start", json={"session_id": sid, "anchor": {"kind": "text", "quote": "Our survey"}})

    for _ in range(2):
        resp = client.post("/explore/message", json={"session_id": sid, "message": "tell me more"})
        assert resp.status_code == 200

    over_cap = client.post("/explore/message", json={"session_id": sid, "message": "one more"})
    assert over_cap.status_code == 409


def test_explore_is_not_gated_by_the_graded_turn_guard():
    """Exploring is independent of the 3-5 turn graded dialogue's completion state."""
    sid = new_session()
    reply = None
    for _ in range(config.MAX_TURNS):
        reply = client.post(
            "/chat",
            json={"session_id": sid, "message": "Why does this happen and what else could explain it?"},
        ).json()
    assert reply["is_complete"] is True

    start = client.post("/explore/start", json={"session_id": sid, "anchor": {"kind": "text", "quote": "Our survey"}})
    assert start.status_code == 200


# --- isolation from grading ---------------------------------------------------------


def test_explore_thread_never_affects_the_rubric_report():
    exchange = Exchange(
        index=1,
        student_message="Maybe something else caused both, like study habits, unless the sample was biased.",
        llm_response="What would you need to find out before you believed that?",
    )
    baseline = Session(
        session_id="s1", content_id="screen-time-scores", min_turns=1, max_turns=1, exchanges=[exchange]
    )
    with_explore = Session(
        session_id="s2", content_id="screen-time-scores", min_turns=1, max_turns=1, exchanges=[exchange]
    )
    # A long, doubt-laden explore thread would shift the heuristic's signals if it leaked in.
    with_explore.explore = ExploreThread(
        anchor_excerpt="the chart",
        messages=[
            ExploreMessage(
                student_message="assume cause bias correlate maybe might could unless " * 5,
                llm_response="r",
            )
        ],
    )

    baseline_dims = evaluator._heuristic_scores(baseline)
    explore_dims = evaluator._heuristic_scores(with_explore)
    assert baseline_dims == explore_dims
