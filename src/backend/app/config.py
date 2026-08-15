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
MAX_HINTS_PER_TURN = int(os.getenv("MAX_HINTS_PER_TURN", "3"))

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


@lru_cache(maxsize=1)
def load_rubric() -> dict:
    return json.loads((DATA_DIR / "rubric.json").read_text(encoding="utf-8"))


def llm_enabled() -> bool:
    """Whether a real LLM is reachable. When false the app runs in stub mode."""
    return bool(GITHUB_TOKEN)
