from __future__ import annotations

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
- Feedback is addressed directly to the student as "you", is specific, and names what to do differently.
- Write feedback and the explanation in short sentences with everyday words a 6th grader knows.
- The explanation must describe how the student's thinking moved across the conversation."""


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
        lines.append(f"Student (turn {exchange.index}){anchor}: {exchange.student_message}")
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


def _heuristic_scores(session: Session) -> dict:
    """Deterministic fallback so the prototype demos without a token.

    Signals are crude on purpose: they reward length, specificity, question
    marks, and reference to earlier turns.
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
    avg_len = sum(len(m.split()) for m in messages) / max(1, len(messages))
    builds = len(messages) >= 3

    raw = {
        "question_quality": clamp(1 + int(has_question) + int(avg_len > 12)),
        "evidence_reasoning": clamp(1 + int(has_number) + int(avg_len > 15)),
        "assumption_awareness": clamp(1 + 2 * int(has_doubt)),
        "depth_of_followup": clamp(1 + int(builds) + int(len(messages) >= 4)),
        "synthesis": clamp(1 + int(avg_len > 18) + int(has_doubt and builds)),
    }

    dimensions = []
    for dim in rubric["dimensions"]:
        score = raw[dim["id"]]
        quote = max(messages, key=len) if messages else ""
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
    )
