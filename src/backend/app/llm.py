from __future__ import annotations

import json
import logging
from contextvars import ContextVar

from . import config

logger = logging.getLogger(__name__)

_client = None

_force_stub: ContextVar[bool] = ContextVar("force_stub", default=False)
"""Per-request switch to the scripted path, set from the session's llm_mode.

A ContextVar rather than a module global because the choice belongs to one
session: two students demoing side by side must not flip each other's mode.
It is also why this isn't threaded through as an argument -- explore.py and
generator.py never receive a Session, so a parameter would have to be pushed
through several unrelated signatures to reach the one place that reads it.
"""


def set_stub_mode(force: bool) -> None:
    """Force the stub path for the current request only."""
    _force_stub.set(force)


def _get_client():
    global _client
    if _client is None:
        from openai import OpenAI

        # The SDK insists on a non-empty key even when the server ignores it, which is
        # the case for local OpenAI-compatible servers.
        _client = OpenAI(
            base_url=config.LLM_BASE_URL,
            api_key=config.LLM_API_KEY or "local-no-key-needed",
        )
    return _client


class LLMUnavailable(Exception):
    """Raised when no token is configured or the provider call fails."""


def complete_json(
    system_prompt: str,
    user_prompt: str,
    schema_name: str,
    schema: dict,
    temperature: float = 0.4,
) -> dict:
    """Call the model and return JSON validated against a schema.

    Structured output is deliberate: rubric scoring must always yield every
    dimension with an evidence quote, and free-text parsing fails under demo
    conditions in ways that are hard to recover from.
    """
    if _force_stub.get():
        raise LLMUnavailable("stub mode selected for this session")

    if not config.llm_enabled():
        raise LLMUnavailable("no LLM configured: set GITHUB_TOKEN or point LLM_BASE_URL at a local server")

    try:
        response = _get_client().chat.completions.create(
            model=config.LLM_MODEL,
            temperature=temperature,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            response_format={
                "type": "json_schema",
                "json_schema": {"name": schema_name, "strict": True, "schema": schema},
            },
        )
        return json.loads(response.choices[0].message.content)
    except Exception as exc:  # noqa: BLE001 - any provider failure falls back to stub
        logger.warning("LLM call failed, falling back to stub: %s", exc)
        raise LLMUnavailable(str(exc)) from exc
