"""Verification and event-filtering for StudyLife's outgoing webhooks - see
studylife-webhooks/src/studylife_webhooks/delivery.py for the exact signing scheme this
mirrors: HMAC-SHA256 of the raw JSON body using the per-webhook secret, hex-encoded.
"""

from __future__ import annotations

import hashlib
import hmac

_ANNOUNCEMENT_EVENT_TYPES = {"timer.started", "timer.ended"}


def verify_webhook_signature(secret: str, signature_hex: str, body: bytes) -> bool:
    expected = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature_hex)


def wants_announcement(event_type: object) -> bool:
    return event_type in _ANNOUNCEMENT_EVENT_TYPES
