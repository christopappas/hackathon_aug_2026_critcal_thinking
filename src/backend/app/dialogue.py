from __future__ import annotations

from .llm import LLMUnavailable, complete_json
from .models import Session

DIALOGUE_SCHEMA = {
    "type": "object",
    "properties": {
        "reply": {
            "type": "string",
            "description": "A short Socratic follow-up that deepens the student's thinking.",
        },
        "rubric_evidence_seen": {
            "type": "array",
            "items": {
                "type": "string",
                "enum": [
                    "question_quality",
                    "evidence_reasoning",
                    "assumption_awareness",
                    "depth_of_followup",
                    "synthesis",
                ],
            },
            "description": "Rubric dimensions for which this exchange produced observable evidence.",
        },
        "should_conclude": {
            "type": "boolean",
            "description": "True when enough evidence exists across all rubric dimensions.",
        },
    },
    "required": ["reply", "rubric_evidence_seen", "should_conclude"],
    "additionalProperties": False,
}

SYSTEM_PROMPT = """You are a Socratic tutor for a 6th grade student, about 11 or 12 years old.

Your job is to deepen the student's thinking about a piece of content. You must NOT:
- give the student the answer or your own verdict on the content
- tell the student their score, mention a rubric, or evaluate them
- lecture, or write more than 3 sentences

You MUST:
- respond to what the student actually said, building on their exact words
- ask exactly one follow-up question that pushes one level deeper
- escalate: if they noticed something, ask why it matters or what would test it
- be warm and curious, never condescending

Write for a 6th grader:
- short sentences, everyday words, no jargon
- if you need a term like "sample size" or "cause", explain it in a few plain words
- never use words a 6th grader would have to look up

If the student anchored their message to part of the content, reference that part directly."""


def _history_block(session: Session) -> str:
    if not session.exchanges:
        return "(this is the student's first message)"
    lines = []
    for exchange in session.exchanges:
        lines.append(f"Student: {exchange.student_message}")
        lines.append(f"You: {exchange.llm_response}")
    return "\n".join(lines)


def build_user_prompt(
    session: Session, content: dict, message: str, anchor_excerpt: str | None
) -> str:
    anchor_line = (
        f"The student anchored this message to {anchor_excerpt}."
        if anchor_excerpt
        else "The student did not anchor this message to a specific part."
    )
    return f"""CONTENT THE STUDENT IS EXAMINING
Title: {content['title']}
Reading level: grade {content.get('grade_level', 6)}
Text: {content['body']}
Chart: {content['chart']['alt']}

CONVERSATION SO FAR
{_history_block(session)}

{anchor_line}

STUDENT'S NEW MESSAGE
{message}

This is exchange {session.turns_used + 1} of at most {session.max_turns}.
{"This is the final exchange, so end with a question that invites them to state their overall position." if session.turns_used + 1 >= session.max_turns else ""}"""


_STUB_REPLIES = [
    "That is a good place to start. What would you need to find out before you believed that part?",
    "You are onto something. If that is not the real reason, what else could explain it?",
    "Nice - you named another possible reason. What one piece of evidence would tell you which reason is right?",
    "Look for anything here that does not fit the pattern. How does that change the conclusion?",
    "Last one: if you wrote one sentence back to whoever made this, what would you tell them their evidence really shows?",
]


def _stub_response(session: Session) -> dict:
    reply = _STUB_REPLIES[min(session.turns_used, len(_STUB_REPLIES) - 1)]
    return {
        "reply": reply,
        "rubric_evidence_seen": ["question_quality"],
        "should_conclude": session.turns_used + 1 >= session.max_turns,
    }


def generate_followup(
    session: Session, content: dict, message: str, anchor_excerpt: str | None
) -> tuple[dict, bool]:
    """Return the follow-up payload and whether a real LLM produced it."""
    try:
        payload = complete_json(
            SYSTEM_PROMPT,
            build_user_prompt(session, content, message, anchor_excerpt),
            "socratic_followup",
            DIALOGUE_SCHEMA,
            temperature=0.7,
        )
        return payload, True
    except LLMUnavailable:
        return _stub_response(session), False


HINT_SCHEMA = {
    "type": "object",
    "properties": {
        "hint": {
            "type": "string",
            "description": "A short hint toward the student's next question, matched to the requested level.",
        },
    },
    "required": ["hint"],
    "additionalProperties": False,
}

HINT_SYSTEM_PROMPT = """You are a Socratic tutor giving a hint to a 6th grade student, about 11 or 12 years old, who is stuck on what to ask next.

Hints come in three levels, each more direct than the last:
- Level 1: point at *where* to look in the content, without saying what's wrong with it.
- Level 2: name the *kind* of thinking move to try (e.g. checking whether two things happening together really means one caused the other), without applying it to this content yet.
- Level 3: get close to naming the actual issue in this content, but still leave the final step to the student.

You MUST NOT, at any level:
- write a question the student could copy word-for-word as their own message
- give the student the answer or your own verdict on the content
- say "critical thinking," mention a rubric, or say anything about scoring
- write more than 2 sentences

Write for a 6th grader: short sentences, everyday words, no jargon."""


def build_hint_prompt(
    session: Session, content: dict, anchor_excerpt: str | None, hint_level: int
) -> str:
    anchor_line = (
        f"The student anchored their attention to {anchor_excerpt}."
        if anchor_excerpt
        else "The student has not anchored their attention to a specific part."
    )
    return f"""CONTENT THE STUDENT IS EXAMINING
Title: {content['title']}
Reading level: grade {content.get('grade_level', 6)}
Text: {content['body']}
Chart: {content['chart']['alt']}

CONVERSATION SO FAR
{_history_block(session)}

{anchor_line}

The student asked for a hint. Give a level {hint_level} hint."""


_STUB_HINTS = [
    "Look back at the part you're curious about. Does it actually say that, or does it just seem to say that?",
    "Two things happening at the same time is not proof that one caused the other. Is that happening here?",
    "Try asking what else could explain the same result. That question is your next move.",
]


def _stub_hint(hint_level: int) -> str:
    return _STUB_HINTS[min(hint_level - 1, len(_STUB_HINTS) - 1)]


def generate_hint(
    session: Session, content: dict, anchor_excerpt: str | None, hint_level: int
) -> tuple[str, bool]:
    """Return the hint text and whether a real LLM produced it."""
    try:
        payload = complete_json(
            HINT_SYSTEM_PROMPT,
            build_hint_prompt(session, content, anchor_excerpt, hint_level),
            "socratic_hint",
            HINT_SCHEMA,
            temperature=0.6,
        )
        return payload["hint"], True
    except LLMUnavailable:
        return _stub_hint(hint_level), False
