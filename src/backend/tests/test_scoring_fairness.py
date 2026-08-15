"""Scoring must not reward verbosity.

The offline heuristic used to gate three of five dimensions on average message
length, which measured typing stamina rather than thinking and penalised
students who write less -- notably dyslexic students. These tests pin the
property that matters: identical reasoning scores identically regardless of how
many words carry it.
"""

from __future__ import annotations

from app import evaluator
from app.models import AccessProfile, Exchange, Session

# The same reasoning move -- questioning the claim and naming a rival cause --
# carried by identical markers, differing only in how many words surround them.
TERSE = "why? maybe another cause because data"
VERBOSE = (
    "I was really just sitting here wondering, why? maybe another cause because data "
    "and that is the kind of thing I keep coming back to whenever I read one of these"
)


def make_session(*messages: str, profile: AccessProfile | None = None) -> Session:
    return Session(
        session_id="s1",
        content_id="c1",
        min_turns=3,
        max_turns=5,
        exchanges=[
            Exchange(index=i + 1, student_message=m, llm_response="r")
            for i, m in enumerate(messages)
        ],
        access_profile=profile or AccessProfile(),
    )


def scores(session: Session) -> dict[str, int]:
    payload = evaluator._heuristic_scores(session)
    return {d["dimension"]: d["score"] for d in payload["dimensions"]}


def test_short_and_long_messages_with_equal_reasoning_score_the_same():
    terse = scores(make_session(TERSE, TERSE, TERSE))
    verbose = scores(make_session(VERBOSE, VERBOSE, VERBOSE))
    assert terse == verbose


def test_padding_a_message_does_not_raise_any_score():
    padding = "and I kept on writing many many more words all across the page"
    base = scores(make_session(TERSE, TERSE, TERSE))
    padded = scores(make_session(f"{TERSE} {padding}", TERSE, TERSE))
    assert all(padded[dim] <= base[dim] for dim in base)


def test_filler_words_do_not_trip_reasoning_signals():
    """"also" contains "so", "different" contains "if" -- neither is reasoning."""
    filler = scores(make_session("also different stuff", "also different stuff"))
    assert filler["evidence_reasoning"] == 1


def test_reasoning_markers_still_earn_credit():
    """Guard against the fix flattening scoring into a constant."""
    empty = scores(make_session("ok", "sure", "fine"))
    reasoned = scores(
        make_session(
            "why does it say that?",
            "I assume they might be wrong because the numbers could be biased",
            "we could test it another way instead",
        )
    )
    assert sum(reasoned.values()) > sum(empty.values())


def test_evidence_quote_prefers_reasoning_over_length():
    session = make_session("this is a very long message that simply says nothing at all", TERSE)
    payload = evaluator._heuristic_scores(session)
    assert all(d["evidence_quote"] == TERSE for d in payload["dimensions"])


def test_report_records_accommodations_when_profile_is_set():
    session = make_session(TERSE, TERSE, TERSE, profile=AccessProfile(dyslexia_support=True))
    report = evaluator.build_report(session, {"body": "content"})
    assert report.accommodations == ["Dyslexia-friendly reading mode"]


def test_report_has_no_accommodations_by_default():
    report = evaluator.build_report(make_session(TERSE), {"body": "content"})
    assert report.accommodations == []
