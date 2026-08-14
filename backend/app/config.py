from __future__ import annotations

import json
import os
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

DATA_DIR = Path(__file__).parent / "data"
STATIC_DIR = Path(__file__).parent / "static"

MIN_TURNS = int(os.getenv("MIN_TURNS", "3"))
MAX_TURNS = int(os.getenv("MAX_TURNS", "5"))

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://models.inference.ai.azure.com")
LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4o-mini")

CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")


@lru_cache(maxsize=1)
def load_content() -> dict:
    return json.loads((DATA_DIR / "content.json").read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def load_rubric() -> dict:
    return json.loads((DATA_DIR / "rubric.json").read_text(encoding="utf-8"))


def llm_enabled() -> bool:
    """Whether a real LLM is reachable. When false the app runs in stub mode."""
    return bool(GITHUB_TOKEN)
