from __future__ import annotations

import json
import logging

from . import config

logger = logging.getLogger(__name__)

_client = None


def _get_client():
    global _client
    if _client is None:
        from openai import OpenAI

        _client = OpenAI(base_url=config.LLM_BASE_URL, api_key=config.GITHUB_TOKEN)
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
    if not config.llm_enabled():
        raise LLMUnavailable("no GITHUB_TOKEN configured")

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
