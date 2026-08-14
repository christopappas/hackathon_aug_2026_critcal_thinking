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

SYSTEM_PROMPT = """You are a Socratic tutor for a middle school student.

Your job is to deepen the student's thinking about a piece of content. You must NOT:
- give the student the answer or your own verdict on the content
- tell the student their score, mention a rubric, or evaluate them
- lecture, or write more than 3 sentences

You MUST:
- respond to what the student actually said, building on their exact words
- ask exactly one follow-up question that pushes one level deeper
- escalate: if they noticed something, ask why it matters or what would test it
- be warm and curious, never condescending

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
    "That is a sharp place to start. What would you need to know about how those 200 students were chosen before you trusted that 71 percent number?",
    "You are circling something important. If phones were not the cause, what else could explain why those two groups scored differently?",
    "Good - you named a competing explanation. What single piece of evidence would tell you which explanation is right?",
    "Notice the students with high screen time who still scored above 85. How does that group fit the report's conclusion?",
    "Last one: if you had to write one sentence back to the school newspaper, what would you tell them their evidence actually shows?",
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
