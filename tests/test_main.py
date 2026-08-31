from __future__ import annotations

import hashlib
import hmac
import json
import time

import pytest
from fastapi.testclient import TestClient

import studylife_discord.main as main_module
from conftest import sign
from fakes import FakeClient
from studylife_discord.main import app

WEBHOOK_SECRET = "test-webhook-secret"


def _interaction_headers(body: bytes) -> dict[str, str]:
    timestamp = str(int(time.time()))
    return {
        "X-Signature-Ed25519": sign(timestamp, body),
        "X-Signature-Timestamp": timestamp,
        "Content-Type": "application/json",
    }


def _webhook_headers(body: bytes, secret: str = WEBHOOK_SECRET) -> dict[str, str]:
    signature = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return {"X-StudyLife-Webhook-Signature": signature, "Content-Type": "application/json"}


# ---------------------------------------------------------------------------
# POST /interactions
# ---------------------------------------------------------------------------


def test_interactions_invalid_signature_is_rejected() -> None:
    body = json.dumps({"type": 1}).encode()

    with TestClient(app) as client:
        response = client.post(
            "/interactions",
            content=body,
            headers={
                "X-Signature-Ed25519": "00" * 64,
                "X-Signature-Timestamp": str(int(time.time())),
                "Content-Type": "application/json",
            },
        )

    assert response.status_code == 401


def test_interactions_ping_returns_pong() -> None:
    body = json.dumps({"type": 1}).encode()

    with TestClient(app) as client:
        response = client.post("/interactions", content=body, headers=_interaction_headers(body))

    assert response.status_code == 200
    assert response.json() == {"type": 1}


def test_interactions_application_command_dispatches_to_client(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    body = json.dumps({"type": 2, "data": {"name": "kurse", "options": []}}).encode()

    with TestClient(app) as client:
        monkeypatch.setattr(
            app.state, "studylife_client", FakeClient(courses=[{"id": 1}, {"id": 2}])
        )
        response = client.post("/interactions", content=body, headers=_interaction_headers(body))

    assert response.status_code == 200
    payload = response.json()
    assert payload["type"] == 4
    assert "2 Kurse" in payload["data"]["content"]


def test_interactions_unsupported_type_returns_400() -> None:
    body = json.dumps({"type": 3}).encode()

    with TestClient(app) as client:
        response = client.post("/interactions", content=body, headers=_interaction_headers(body))

    assert response.status_code == 400


# ---------------------------------------------------------------------------
# POST /webhooks/studylife
# ---------------------------------------------------------------------------


def test_webhook_invalid_signature_is_rejected() -> None:
    body = json.dumps({"event_type": "timer.started", "payload": {"sessionId": 1}}).encode()

    with TestClient(app) as client:
        response = client.post(
            "/webhooks/studylife",
            content=body,
            headers={
                "X-StudyLife-Webhook-Signature": "not-the-right-signature",
                "Content-Type": "application/json",
            },
        )

    assert response.status_code == 401


def test_webhook_timer_started_announces_course_name(monkeypatch: pytest.MonkeyPatch) -> None:
    body = json.dumps({"event_type": "timer.started", "payload": {"sessionId": 42}}).encode()
    calls: list[tuple[str, str, str]] = []

    async def fake_post_channel_message(bot_token: str, channel_id: str, content: str) -> None:
        calls.append((bot_token, channel_id, content))

    with TestClient(app) as client:
        monkeypatch.setattr(
            app.state, "studylife_client", FakeClient(session_by_id={42: {"courseName": "Mathe"}})
        )
        monkeypatch.setattr(main_module, "post_channel_message", fake_post_channel_message)
        response = client.post("/webhooks/studylife", content=body, headers=_webhook_headers(body))

    assert response.status_code == 200
    assert len(calls) == 1
    bot_token, channel_id, content = calls[0]
    assert bot_token == "test-bot-token"
    assert channel_id == "9876543210"
    assert "Mathe" in content
    assert "gestartet" in content


def test_webhook_non_announcement_event_does_not_post(monkeypatch: pytest.MonkeyPatch) -> None:
    body = json.dumps({"event_type": "note.created", "payload": {}}).encode()
    calls: list[tuple[str, str, str]] = []

    async def fake_post_channel_message(bot_token: str, channel_id: str, content: str) -> None:
        calls.append((bot_token, channel_id, content))

    with TestClient(app) as client:
        monkeypatch.setattr(app.state, "studylife_client", FakeClient())
        monkeypatch.setattr(main_module, "post_channel_message", fake_post_channel_message)
        response = client.post("/webhooks/studylife", content=body, headers=_webhook_headers(body))

    assert response.status_code == 200
    assert calls == []
