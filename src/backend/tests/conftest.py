"""Test-wide isolation from whatever a developer happens to have in their .env.

`config` reads the environment at import time, so a real key in .env leaks into the
suite. That matters because `llm_enabled()` is true if *either* a key is set or
LLM_BASE_URL is non-default, so the tests asserting a stub fallback would quietly
make live API calls and fail -- or, worse, pass only because the provider happened
to rate-limit at that moment.

Individual tests still blank `GITHUB_TOKEN` themselves; that alone stopped being
sufficient once `LLM_API_KEY` was introduced.
"""

from __future__ import annotations

import pytest

from app import config


@pytest.fixture(autouse=True)
def force_stub_mode(monkeypatch):
    """Default every test to offline stub mode; opt in explicitly to test live paths."""
    monkeypatch.setattr(config, "GITHUB_TOKEN", "")
    monkeypatch.setattr(config, "LLM_API_KEY", "")
    monkeypatch.setattr(config, "LLM_BASE_URL", config.DEFAULT_LLM_BASE_URL)
