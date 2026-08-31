from __future__ import annotations

import hashlib
import hmac

from studylife_discord.webhooks import verify_webhook_signature, wants_announcement

SECRET = "test-webhook-secret"
BODY = b'{"event_type":"timer.started","payload":{"sessionId":1}}'


def _hmac_hex(secret: str, body: bytes) -> str:
    return hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


def test_correct_hmac_signature_is_accepted() -> None:
    signature = _hmac_hex(SECRET, BODY)

    assert verify_webhook_signature(SECRET, signature, BODY) is True


def test_wrong_secret_is_rejected() -> None:
    signature = _hmac_hex("some-other-secret", BODY)

    assert verify_webhook_signature(SECRET, signature, BODY) is False


def test_tampered_body_is_rejected() -> None:
    signature = _hmac_hex(SECRET, BODY)

    assert verify_webhook_signature(SECRET, signature, b'{"event_type":"timer.ended"}') is False


def test_garbage_signature_is_rejected_without_crashing() -> None:
    assert verify_webhook_signature(SECRET, "not-a-real-signature", BODY) is False


def test_wants_announcement_true_for_timer_started() -> None:
    assert wants_announcement("timer.started") is True


def test_wants_announcement_true_for_timer_ended() -> None:
    assert wants_announcement("timer.ended") is True


def test_wants_announcement_false_for_session_created() -> None:
    assert wants_announcement("session.created") is False


def test_wants_announcement_false_for_note_created() -> None:
    assert wants_announcement("note.created") is False


def test_wants_announcement_false_for_non_string_event_type() -> None:
    assert wants_announcement(None) is False
