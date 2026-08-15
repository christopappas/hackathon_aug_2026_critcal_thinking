from __future__ import annotations

import json
import os
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

DATA_DIR = Path(__file__).parent / "data"
CONTENT_DIR = DATA_DIR / "content"
STATIC_DIR = Path(__file__).parent / "static"

MIN_TURNS = int(os.getenv("MIN_TURNS", "3"))
MAX_TURNS = int(os.getenv("MAX_TURNS", "5"))
MAX_TURNS_CEILING = 10
"""Sanity cap on a content template's own max_turns override - see content_turn_range()."""
MAX_HINTS_PER_TURN = int(os.getenv("MAX_HINTS_PER_TURN", "3"))
MAX_EXPLORE_MESSAGES = int(os.getenv("MAX_EXPLORE_MESSAGES", "30"))
"""Anti-abuse ceiling on an explore thread, not a pedagogical turn limit like MAX_TURNS."""

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://models.inference.ai.azure.com")
LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4o-mini")

CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")


@lru_cache(maxsize=1)
def load_library() -> dict[str, dict]:
    """Every content piece, keyed by id. Adding content is dropping in a JSON file."""
    items = [
        json.loads(path.read_text(encoding="utf-8"))
        for path in sorted(CONTENT_DIR.glob("*.json"))
    ]
    items.sort(key=lambda item: item.get("order", 999))
    return {item["id"]: item for item in items}


def list_content() -> list[dict]:
    """Lightweight catalog for the picker screen."""
    return [
        {
            "id": item["id"],
            "title": item["title"],
            "subject": item.get("subject", ""),
            "blurb": item.get("blurb", ""),
            "grade_level": item.get("grade_level"),
        }
        for item in load_library().values()
    ]


def default_content_id() -> str:
    return next(iter(load_library()))


def load_content(content_id: str | None = None) -> dict:
    library = load_library()
    if content_id is None:
        return library[default_content_id()]
    if content_id not in library:
        raise KeyError(content_id)
    return library[content_id]


def content_turn_range(content: dict) -> tuple[int, int]:
    """The (min_turns, max_turns) for a session on this content.

    A template may override the global MIN_TURNS/MAX_TURNS with its own
    min_turns/max_turns keys - some lessons warrant a shorter or longer
    exchange than the default. Validated here so a malformed template fails
    loudly at session-creation time instead of producing a broken session.
    """
    min_turns = content.get("min_turns", MIN_TURNS)
    max_turns = content.get("max_turns", MAX_TURNS)
    content_id = content.get("id", "<unknown>")
    if min_turns < 1:
        raise ValueError(f"{content_id}: min_turns must be at least 1, got {min_turns}")
    if max_turns < min_turns:
        raise ValueError(
            f"{content_id}: max_turns ({max_turns}) is less than min_turns ({min_turns})"
        )
    if max_turns > MAX_TURNS_CEILING:
        raise ValueError(
            f"{content_id}: max_turns ({max_turns}) exceeds the ceiling of {MAX_TURNS_CEILING}"
        )
    return min_turns, max_turns


@lru_cache(maxsize=1)
def load_rubric() -> dict:
    return json.loads((DATA_DIR / "rubric.json").read_text(encoding="utf-8"))


def llm_enabled() -> bool:
    """Whether a real LLM is reachable. When false the app runs in stub mode."""
    return bool(GITHUB_TOKEN)
