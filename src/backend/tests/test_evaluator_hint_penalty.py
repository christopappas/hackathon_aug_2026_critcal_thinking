from __future__ import annotations

from app import evaluator
from app.models import DimensionScore, Exchange, Session

DOCKED = evaluator._HINT_DOCKED_DIMENSIONS


def make_dimensions(**scores: int) -> list[DimensionScore]:
    return [
        DimensionScore(dimension=dim_id, name=dim_id, score=score, evidence_quote="q", feedback="f")
        for dim_id, score in scores.items()
    ]


def make_session(*hint_counts: int) -> Session:
    exchanges = [
        Exchange(index=i + 1, student_message="m", llm_response="r", hints_used=count)
        for i, count in enumerate(hint_counts)
    ]
    return Session(session_id="s1", content_id="c1", min_turns=3, max_turns=5, exchanges=exchanges)


def test_no_hints_means_no_penalty():
    dims = make_dimensions(question_quality=4, evidence_reasoning=4, assumption_awareness=4)
    evaluator._apply_hint_penalty(dims, make_session(0, 1))
    assert [d.score for d in dims] == [4, 4, 4]
    assert all("hint" not in d.feedback.lower() for d in dims)


def test_two_hints_docks_only_the_hint_assisted_dimensions_by_one():
    dims = make_dimensions(question_quality=4, evidence_reasoning=3, assumption_awareness=4)
    evaluator._apply_hint_penalty(dims, make_session(2))
    by_id = {d.dimension: d for d in dims}
    assert by_id["question_quality"].score == 3
    assert by_id["evidence_reasoning"].score == 2
    assert by_id["assumption_awareness"].score == 4
    assert "hint use" in by_id["question_quality"].feedback.lower()
    assert "hint" not in by_id["assumption_awareness"].feedback.lower()


def test_penalty_caps_at_two_even_with_many_hints():
    dims = make_dimensions(question_quality=4)
    evaluator._apply_hint_penalty(dims, make_session(3, 3))  # 6 hints total
    assert dims[0].score == 2


def test_penalty_floors_at_one_and_does_not_relabel_unchanged_scores():
    dims = make_dimensions(question_quality=1)
    evaluator._apply_hint_penalty(dims, make_session(3))
    assert dims[0].score == 1
    assert dims[0].feedback == "f"


def test_only_docked_dimension_ids_are_ever_touched():
    non_docked_ids = {"assumption_awareness", "depth_of_followup", "synthesis"}
    assert DOCKED.isdisjoint(non_docked_ids)
