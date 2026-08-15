"""The educator sets accommodations in advance; the session must carry them."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_session_defaults_to_no_accommodations():
    response = client.post("/session", json={})
    assert response.status_code == 200
    assert response.json()["access_profile"] == {"dyslexia_support": False}


def test_session_accepts_and_echoes_the_access_profile():
    response = client.post(
        "/session",
        json={"access_profile": {"dyslexia_support": True}},
    )
    assert response.status_code == 200
    assert response.json()["access_profile"]["dyslexia_support"] is True


def test_profile_survives_to_the_report():
    session_id = client.post(
        "/session",
        json={"access_profile": {"dyslexia_support": True}},
    ).json()["session_id"]

    for _ in range(5):
        response = client.post(
            "/chat", json={"session_id": session_id, "message": "why is that?"}
        )
        if response.json()["is_complete"]:
            break

    report = client.get(f"/report/{session_id}")
    assert report.status_code == 200
    assert report.json()["accommodations"] == ["Dyslexia-friendly reading mode"]


def test_unknown_content_id_still_404s_with_a_profile():
    response = client.post(
        "/session",
        json={"content_id": "nope", "access_profile": {"dyslexia_support": True}},
    )
    assert response.status_code == 404
