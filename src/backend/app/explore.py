from __future__ import annotations

from .llm import LLMUnavailable, complete_json
from .models import ExploreThread

EXPLORE_SCHEMA = {
    "type": "object",
    "properties": {
        "reply": {
            "type": "string",
            "description": "A short, curious reply that keeps the discussion going on this one spot.",
        },
    },
    "required": ["reply"],
    "additionalProperties": False,
}

EXPLORE_SYSTEM_PROMPT = """You are a curious discussion partner for a 6th grade student, about 11 or 12 years old.

The student clicked or highlighted one specific spot in a piece of content because it caught
their eye. This is a free-ranging, unscored side conversation about just that spot - not a
quiz, not the graded exercise. Your job is to help them go deeper on their own curiosity.

You MUST NOT:
- mention a rubric, a score, or that this conversation is unscored
- lecture, or write more than 3 sentences

You SHOULD:
- respond to what the student actually said, building on their exact words
- ask a genuine follow-up question, OR occasionally offer one interesting related fact and then
  ask what the student thinks of it - more conversational than a strict one-question drill
- be warm, curious, and never condescending

Write for a 6th grader: short sentences, everyday words, no jargon."""


def _history_block(thread: ExploreThread) -> str:
    if not thread.messages:
        return "(this is the student's first message in this discussion)"
    lines = []
    for message in thread.messages:
        lines.append(f"Student: {message.student_message}")
        lines.append(f"You: {message.llm_response}")
    return "\n".join(lines)


def build_opening_prompt(content: dict, anchor_excerpt: str | None) -> str:
    anchor_line = (
        f"The student is curious about {anchor_excerpt}."
        if anchor_excerpt
        else "The student is curious about this content but did not point at a specific part."
    )
    return f"""CONTENT THE STUDENT IS EXAMINING
Title: {content['title']}
Reading level: grade {content.get('grade_level', 6)}
Text: {content['body']}
Chart: {content['chart']['alt']}

{anchor_line}

Open the discussion: react to that specific spot in one or two sentences, then invite the
student to share what they're thinking."""


def build_message_prompt(thread: ExploreThread, content: dict, message: str) -> str:
    anchor_line = (
        f"The discussion is about {thread.anchor_excerpt}."
        if thread.anchor_excerpt
        else "The discussion is about the content in general."
    )
    return f"""CONTENT THE STUDENT IS EXAMINING
Title: {content['title']}
Reading level: grade {content.get('grade_level', 6)}
Text: {content['body']}
Chart: {content['chart']['alt']}

{anchor_line}

DISCUSSION SO FAR
{_history_block(thread)}

STUDENT'S NEW MESSAGE
{message}"""


_STUB_OPENERS = [
    "Interesting choice to look at! What made you stop there?",
    "That part stood out to you for a reason. What's your first thought about it?",
    "Good spot to dig into. What do you notice when you look closely?",
]

_DOUBT_WORDS = ("maybe", "might", "could", "unless", "assume", "probably", "i think", "not sure")


def _stub_opening(anchor_excerpt: str | None) -> str:
    if anchor_excerpt:
        return f"You picked out {anchor_excerpt}. What made you stop there?"
    return _STUB_OPENERS[0]


def _snippet(text: str, limit: int = 50) -> str:
    text = text.strip()
    if len(text) <= limit:
        return text
    return text[:limit].rsplit(" ", 1)[0] + "..."


def _stub_reply(message: str) -> str:
    """A reply shaped by what the student actually just wrote, not a canned rotation.

    There's no LLM in this path, so this is deliberately crude keyword-matching rather
    than real understanding - but it beats cycling through fixed lines regardless of
    what was typed, which is what made offline mode feel like it wasn't listening.
    """
    snippet = _snippet(message)
    lower = message.lower()

    if "?" in message:
        return f'Good question. Before I answer - what\'s your own best guess about "{snippet}"?'
    if any(word in lower for word in _DOUBT_WORDS):
        return f'You hedged on "{snippet}" - what would make you more sure either way?'
    if len(message.split()) <= 5:
        return f'Say more about "{snippet}" - what makes you think that?'
    return f'"{snippet}" is a solid point. What would you ask next to test it?'


def generate_opening(content: dict, anchor_excerpt: str | None) -> tuple[str, bool]:
    """Return the opening line for a new explore thread, and whether a real LLM produced it."""
    try:
        payload = complete_json(
            EXPLORE_SYSTEM_PROMPT,
            build_opening_prompt(content, anchor_excerpt),
            "explore_opening",
            EXPLORE_SCHEMA,
            temperature=0.7,
        )
        return payload["reply"], True
    except LLMUnavailable:
        return _stub_opening(anchor_excerpt), False


def generate_reply(thread: ExploreThread, content: dict, message: str) -> tuple[str, bool]:
    """Return the next reply in an explore thread, and whether a real LLM produced it."""
    try:
        payload = complete_json(
            EXPLORE_SYSTEM_PROMPT,
            build_message_prompt(thread, content, message),
            "explore_reply",
            EXPLORE_SCHEMA,
            temperature=0.7,
        )
        return payload["reply"], True
    except LLMUnavailable:
        return _stub_reply(message), False
