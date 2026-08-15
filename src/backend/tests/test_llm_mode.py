"""The runtime mock/live switch.

The autouse conftest fixture pins stub mode, so tests that need a configured
provider re-enable it explicitly here rather than relying on a developer's .env.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app import config
from app.main import app

client = TestClient(app)


@pytest.fixture
def provider_configured(monkeypatch):
    """Pretend a provider is reachable without making a network call."""
    monkeypatch.setattr(config, "LLM_API_KEY", "test-key")
    monkeypatch.setattr(config, "LLM_BASE_URL", "https://example.invalid/v1")


def test_session_defaults_to_stub_when_nothing_is_configured():
    """Asking for live with no provider is the normal offline setup, not an error."""
    body = client.post("/session", json={"llm_mode": "live"}).json()
    assert body["llm_mode"] == "stub"
    assert body["llm_enabled"] is False


def test_session_keeps_live_mode_when_a_provider_is_configured(provider_configured):
    body = client.post("/session", json={"llm_mode": "live"}).json()
    assert body["llm_mode"] == "live"


def test_stub_mode_is_honoured_even_with_a_provider_configured(provider_configured, monkeypatch):
    """The whole point of the switch: force the scripted path on demand.

    complete_json is replaced with a call recorder rather than a network stub, so
    a regression that bypasses the mode fails loudly instead of quietly costing
    money and producing a live reply during a mock demo.
    """
    calls: list[str] = []

    def explode(*args, **kwargs):
        calls.append("called")
        raise AssertionError("stub mode must not reach the provider")

    monkeypatch.setattr("app.llm._get_client", explode)

    session_id = client.post("/session", json={"llm_mode": "stub"}).json()["session_id"]
    response = client.post("/chat", json={"session_id": session_id, "message": "why is that?"})

    assert response.status_code == 200
    assert response.json()["reply"]
    assert calls == []


def test_mode_can_be_switched_mid_conversation(provider_configured):
    session_id = client.post("/session", json={"llm_mode": "live"}).json()["session_id"]

    response = client.put(f"/session/{session_id}/llm-mode", json={"llm_mode": "stub"})

    assert response.status_code == 200
    assert response.json()["llm_mode"] == "stub"
    assert response.json()["model"] == config.LLM_MODEL


def test_switching_to_live_without_a_provider_is_rejected():
    """Better a 409 than a dropdown that silently does nothing."""
    session_id = client.post("/session").json()["session_id"]

    response = client.put(f"/session/{session_id}/llm-mode", json={"llm_mode": "live"})

    assert response.status_code == 409


def test_mode_switch_on_an_unknown_session_is_404():
    response = client.put("/session/nope/llm-mode", json={"llm_mode": "stub"})
    assert response.status_code == 404


def test_mode_is_per_session_not_global(provider_configured):
    """Two demos side by side must not flip each other's mode."""
    a = client.post("/session", json={"llm_mode": "live"}).json()
    b = client.post("/session", json={"llm_mode": "stub"}).json()

    assert a["llm_mode"] == "live"
    assert b["llm_mode"] == "stub"
