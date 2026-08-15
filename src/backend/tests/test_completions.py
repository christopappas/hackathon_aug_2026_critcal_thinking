from __future__ import annotations

from fastapi.testclient import TestClient

from app import completions, config, evaluator
from app.main import app

client = TestClient(app)


def fetch() -> dict:
    response = client.get("/teacher/completions")
    assert response.status_code == 200
    return response.json()


def test_completions_are_labelled_as_mock():
    """The badge on the page is driven by this flag, so a demo class can't pass for real."""
    assert fetch()["mock"] is True


def test_every_student_on_the_roster_has_at_least_one_completion():
    body = fetch()
    named = {row["student_name"] for row in body["rows"]}
    assert named == {student for student, _ in completions.MOCK_ROSTER}
    assert body["student_count"] == len(completions.MOCK_ROSTER)


def test_rows_are_stable_across_calls():
    """Seeded per row, so a refresh mid-demo never reshuffles the class."""
    assert fetch()["rows"] == fetch()["rows"]


def test_rows_are_newest_first():
    stamps = [row["completed_at"] for row in fetch()["rows"]]
    assert stamps == sorted(stamps, reverse=True)


def test_every_row_scores_every_rubric_dimension():
    expected = [dim["id"] for dim in config.load_rubric()["dimensions"]]
    for row in fetch()["rows"]:
        assert [dim["dimension"] for dim in row["dimensions"]] == expected
        assert all(1 <= dim["score"] <= 4 for dim in row["dimensions"])


def test_overall_and_bloom_match_what_a_real_report_would_produce():
    """The mock shares the evaluator's arithmetic, so it can't drift into
    a score the scorer itself could never hand out."""
    for row in fetch()["rows"]:
        scores = [dim["score"] for dim in row["dimensions"]]
        assert row["overall_score"] == evaluator.overall_score(scores)
        assert row["bloom_level_reached"] == evaluator.bloom_level(scores)


def test_turns_used_respects_the_content_piece_turn_range():
    for row in fetch()["rows"]:
        content = config.load_content(row["content_id"])
        min_turns, max_turns = config.content_turn_range(content)
        assert min_turns <= row["turns_used"] <= max_turns


def test_completions_only_reference_content_students_can_actually_open():
    published = {item["id"] for item in config.list_content()}
    assert {row["content_id"] for row in fetch()["rows"]} <= published


def test_average_score_matches_the_rows():
    body = fetch()
    rows = body["rows"]
    assert body["average_score"] == round(sum(r["overall_score"] for r in rows) / len(rows), 1)
