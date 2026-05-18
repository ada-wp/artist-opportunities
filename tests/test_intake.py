from __future__ import annotations

import os

import pytest

from artist_resource_project.intake import parse_intake_payload
from artist_resource_project.intake_service import dry_run_intake
from artist_resource_project.render import render_intake_email_html, render_intake_email_text


SAMPLE_PAYLOAD = {
    "name": "Maya Thompson",
    "email": "maya@example.com",
    "primary_medium": "oil painting",
    "style_description": "contemporary figurative painting with tonal atmosphere",
    "themes": "memory, portraiture, migration, identity",
    "budget_cap_usd": 100,
    "minimum_days_until_deadline": 10,
    "career_goal": "exhibition exposure and institutional recognition",
    "eligible_regions": "US",
    "career_stage": "emerging",
}


def test_parse_intake_payload_splits_comma_separated_lists() -> None:
    submission = parse_intake_payload(SAMPLE_PAYLOAD)

    assert submission.name == "Maya Thompson"
    assert submission.themes == ["memory", "portraiture", "migration", "identity"]
    assert submission.eligible_regions == ["US"]


def test_dry_run_intake_returns_recommendations(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("INTAKE_TOP_K", "3")
    submission, payload = dry_run_intake(SAMPLE_PAYLOAD)

    assert submission.email == "maya@example.com"
    assert payload["recipient_email"] == "maya@example.com"
    assert payload["top_recommendations"]
    assert len(payload["top_recommendations"]) <= 3


def test_render_intake_email_includes_disclaimer() -> None:
    _, payload = dry_run_intake(SAMPLE_PAYLOAD)
    text = render_intake_email_text(payload)
    html = render_intake_email_html(payload)

    assert "draft shortlist" in text.lower()
    assert "automated draft" in html.lower()


def test_parse_intake_requires_email() -> None:
    bad_payload = {**SAMPLE_PAYLOAD, "email": "not-an-email"}
    with pytest.raises(ValueError):
        parse_intake_payload(bad_payload)


def test_api_rejects_missing_secret(monkeypatch: pytest.MonkeyPatch) -> None:
    pytest.importorskip("fastapi")
    from fastapi.testclient import TestClient

    from artist_resource_project.api import create_app

    monkeypatch.setenv("INTAKE_WEBHOOK_SECRET", "test-secret")
    client = TestClient(create_app())

    response = client.post("/v1/intake/preview", json=SAMPLE_PAYLOAD)
    assert response.status_code == 401

    response = client.post(
        "/v1/intake/preview",
        json=SAMPLE_PAYLOAD,
        headers={"X-Intake-Secret": "test-secret"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["match_count"] >= 0
