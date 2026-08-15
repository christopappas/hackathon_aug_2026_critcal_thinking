from __future__ import annotations

import re

from .config import load_rubric
from .llm import LLMUnavailable, complete_json
from .models import DimensionScore, Report, Session

BLOOM_LEVELS = ["Remember", "Understand", "Apply", "Analyze", "Evaluate", "Create"]


def _scoring_schema(dimension_ids: list[str]) -> dict:
    return {
        "type": "object",
        "properties": {
            "dimensions": {
                "type": "array",
                "minItems": len(dimension_ids),
                "maxItems": len(dimension_ids),
                "items": {
                    "type": "object",
                    "properties": {
                        "dimension": {"type": "string", "enum": dimension_ids},
                        "score": {"type": "integer", "minimum": 1, "maximum": 4},
                        "evidence_quote": {
                            "type": "string",
                            "description": "A quote taken verbatim from the student's messages.",
                        },
                        "feedback": {
                            "type": "string",
                            "description": "One or two sentences addressed to the student.",
                        },
                    },
                    "required": ["dimension", "score", "evidence_quote", "feedback"],
                    "additionalProperties": False,
                },
            },
            "bloom_level_reached": {"type": "string", "enum": BLOOM_LEVELS},
            "explanation": {"type": "string"},
            "next_step": {"type": "string"},
        },
        "required": ["dimensions", "bloom_level_reached", "explanation", "next_step"],
        "additionalProperties": False,
    }


SYSTEM_PROMPT = """You are an assessment engine scoring a 6th grade student's critical thinking.

Score ONLY the student's own messages. Never score the tutor's questions.

Rules:
- Every dimension score must be justified by a quote taken verbatim from the student.
- If a dimension has no supporting evidence, score it 1 and quote the closest attempt.
- Be fair but not generous. Reserve 4 for genuinely advanced reasoning.
- Judge the thinking, not the spelling, grammar, or typing. A 6th grader writes casually.
- Never reward length. A short, sharp question scores higher than a long vague one. Some
  students type with difficulty; message length is not evidence of thinking.
- Misspellings, phonetic spellings ("becuz", "seperate"), missing punctuation, and run-on
  sentences carry no penalty. Read for intent and score the reasoning underneath.
- Feedback is addressed directly to the student as "you", is specific, and names what to do differently.
- Write feedback and the explanation in short sentences with everyday words a 6th grader knows.
- The explanation must describe how the student's thinking moved across the conversation.
- A turn marked [hints used: N] means the tutor nudged the student toward that message. Weigh
  that turn's evidence as less independent — do not award a 4 on Question Quality or Evidence
  and Reasoning for a turn that leaned on hints."""


def _rubric_block() -> str:
    rubric = load_rubric()
    lines = []
    for dim in rubric["dimensions"]:
        lines.append(f"\n{dim['id']} - {dim['name']} ({dim['bloom_anchor']})")
        lines.append(f"  Measures: {dim['measures']}")
        for level, descriptor in dim["levels"].items():
            lines.append(f"  {level}: {descriptor}")
    return "\n".join(lines)


def _transcript_block(session: Session) -> str:
    lines = []
    for exchange in session.exchanges:
        anchor = f" [anchored to {exchange.anchor_excerpt}]" if exchange.anchor_excerpt else ""
        hints = f" [hints used: {exchange.hints_used}]" if exchange.hints_used else ""
        lines.append(f"Student (turn {exchange.index}){anchor}{hints}: {exchange.student_message}")
        lines.append(f"Tutor: {exchange.llm_response}")
    return "\n".join(lines)


def build_user_prompt(session: Session, content: dict) -> str:
    return f"""RUBRIC
{_rubric_block()}

CONTENT THE STUDENT EXAMINED
{content['body']}

FULL TRANSCRIPT
{_transcript_block(session)}

Score the student on all five dimensions."""


def _mentions(text: str, phrases: tuple[str, ...]) -> bool:
    """Whole-word phrase match.

    Substring matching is too loose for short function words: "so" fires inside
    "also", "if" inside "different". Those false positives would hand out credit
    for filler, which is exactly the verbosity bias this scoring avoids.
    """
    return any(re.search(rf"\b{re.escape(phrase)}\b", text) for phrase in phrases)


def _best_quote(messages: list[str]) -> str:
    """Pick the most reasoning-dense message, not merely the longest one.

    The old rule quoted the longest message, which surfaced rambling over
    insight and made short, sharp answers invisible in the report.
    """
    if not messages:
        return ""
    markers = ("because", "but", "why", "if", "assume", "prove", "evidence", "?")

    def density(message: str) -> tuple[int, int]:
        lowered = message.lower()
        hits = sum(marker in lowered for marker in markers)
        # Length only breaks ties between equally reasoned messages.
        return hits, len(message)

    return max(messages, key=density)


def _heuristic_scores(session: Session) -> dict:
    """Deterministic fallback so the prototype demos without a token.

    Signals are crude on purpose, but they are deliberately *not* length-based.
    Scoring on message length measures typing stamina, not thinking, and
    penalises students who write less -- notably dyslexic students, who may
    reason well in few words. Every signal below looks for a marker of
    reasoning that a short message can satisfy.
    """
    rubric = load_rubric()
    messages = [e.student_message for e in session.exchanges]
    joined = " ".join(messages).lower()

    def clamp(value: int) -> int:
        return max(1, min(4, value))

    has_question = any("?" in m for m in messages)
    has_number = any(char.isdigit() for char in joined)
    doubt_words = ("assume", "cause", "correlat", "maybe", "might", "could", "unless", "bias")
    has_doubt = any(word in joined for word in doubt_words)
    # Causal/contrastive connectives: the student is relating two ideas, not just naming one.
    reasoning_words = ("because", "but", "however", "so", "if", "then", "instead", "even though")
    has_reasoning = _mentions(joined, reasoning_words)
    # Probing question stems, which mark interrogating the claim rather than accepting it.
    probe_words = ("why", "how", "what if", "who", "where", "prove", "evidence", "sure")
    has_probe = _mentions(joined, probe_words)
    # Proposing a test or a rival explanation is the synthesis move.
    synthesis_words = ("test", "compare", "control", "another", "other reason", "explain", "instead")
    has_synthesis = _mentions(joined, synthesis_words)
    builds = len(messages) >= 3

    raw = {
        "question_quality": clamp(1 + int(has_question) + int(has_probe)),
        "evidence_reasoning": clamp(1 + int(has_number) + int(has_reasoning)),
        "assumption_awareness": clamp(1 + 2 * int(has_doubt)),
        "depth_of_followup": clamp(1 + int(builds) + int(len(messages) >= 4)),
        "synthesis": clamp(1 + int(has_synthesis) + int(has_doubt and builds)),
    }

    dimensions = []
    for dim in rubric["dimensions"]:
        score = raw[dim["id"]]
        quote = _best_quote(messages)
        dimensions.append(
            {
                "dimension": dim["id"],
                "score": score,
                "evidence_quote": quote[:180],
                "feedback": dim["levels"][str(min(4, score + 1))]
                if score < 4
                else "You are working at the top of this dimension. Keep it up.",
            }
        )

    total = sum(raw.values())
    level_index = min(len(BLOOM_LEVELS) - 1, max(0, total // 4))
    return {
        "dimensions": dimensions,
        "bloom_level_reached": BLOOM_LEVELS[level_index],
        "explanation": (
            f"Across {len(messages)} messages you asked questions about the report and "
            "worked toward testing its conclusion rather than accepting it."
        ),
        "next_step": "Next time, name the assumption behind a claim and say what evidence would disprove it.",
    }


def evaluate(session: Session, content: dict) -> tuple[dict, bool]:
    rubric = load_rubric()
    dimension_ids = [d["id"] for d in rubric["dimensions"]]
    try:
        payload = complete_json(
            SYSTEM_PROMPT,
            build_user_prompt(session, content),
            "critical_thinking_scores",
            _scoring_schema(dimension_ids),
            temperature=0.1,
        )
        return payload, True
    except LLMUnavailable:
        return _heuristic_scores(session), False


_HINT_DOCKED_DIMENSIONS = {"question_quality", "evidence_reasoning"}


def _apply_hint_penalty(dimensions: list[DimensionScore], session: Session) -> None:
    """Dock the dimensions a hint most directly assists, in place.

    This runs after LLM or heuristic scoring, as a deterministic floor: the
    prompt already asks the model to weigh hint use, but a hackathon demo
    needs the "more hints, less credit" rule to hold even if the model
    ignores it or the heuristic fallback is in play.
    """
    total_hints = sum(exchange.hints_used for exchange in session.exchanges)
    penalty = min(2, total_hints // 2)
    if penalty == 0:
        return
    for dimension in dimensions:
        if dimension.dimension not in _HINT_DOCKED_DIMENSIONS:
            continue
        docked = max(1, dimension.score - penalty)
        if docked == dimension.score:
            continue
        dimension.score = docked
        dimension.feedback = f"{dimension.feedback} Score reflects hint use this session."


def build_report(session: Session, content: dict) -> Report:
    """Evaluate the transcript, then assemble the student-facing report card."""
    payload, used_llm = evaluate(session, content)
    rubric = load_rubric()
    names = {d["id"]: d["name"] for d in rubric["dimensions"]}

    dimensions = [
        DimensionScore(
            dimension=item["dimension"],
            name=names.get(item["dimension"], item["dimension"]),
            score=item["score"],
            evidence_quote=item["evidence_quote"],
            feedback=item["feedback"],
        )
        for item in payload["dimensions"]
    ]
    _apply_hint_penalty(dimensions, session)

    # Five dimensions scored 1-4 gives 5-20; present it on a friendlier 1-10 scale.
    raw_total = sum(d.score for d in dimensions)
    overall = max(1, min(10, round(raw_total / len(dimensions) * 2.5)))

    return Report(
        session_id=session.session_id,
        overall_score=overall,
        bloom_level_reached=payload["bloom_level_reached"],
        explanation=payload["explanation"],
        dimensions=dimensions,
        next_step=payload["next_step"],
        generated_with_llm=used_llm,
        accommodations=session.access_profile.labels(),
    )
