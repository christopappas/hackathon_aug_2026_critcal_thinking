from __future__ import annotations

from app import config, dialogue
from app.models import Session

CONTENT = {
    "title": "Do Phones Hurt Test Scores?",
    "body": "Our survey of 200 students found a link between screen time and test scores.",
    "chart": {"alt": "A scatter plot of screen time versus test score"},
    "grade_level": 6,
}


def make_session() -> Session:
    return Session(session_id="s1", content_id="c1", min_turns=3, max_turns=5)


def test_stub_hint_levels_are_distinct_and_progressive():
    texts = [dialogue._stub_hint(level) for level in (1, 2, 3)]
    assert len(set(texts)) == 3


def test_stub_hint_clamps_beyond_available_levels():
    assert dialogue._stub_hint(3) == dialogue._stub_hint(99)


def test_generate_hint_falls_back_to_stub_without_a_token(monkeypatch):
    monkeypatch.setattr(config, "GITHUB_TOKEN", "")
    text, used_llm = dialogue.generate_hint(make_session(), CONTENT, None, hint_level=2)
    assert used_llm is False
    assert text == dialogue._stub_hint(2)


def test_build_hint_prompt_names_the_requested_level_and_anchor():
    prompt = dialogue.build_hint_prompt(make_session(), CONTENT, "the passage about 200 students", 3)
    assert "level 3 hint" in prompt
    assert "the passage about 200 students" in prompt
    assert CONTENT["title"] in prompt


def test_build_hint_prompt_without_anchor_says_so():
    prompt = dialogue.build_hint_prompt(make_session(), CONTENT, None, 1)
    assert "has not anchored" in prompt
