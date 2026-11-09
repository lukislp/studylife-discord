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
    # Compare bytes: compare_digest() raises TypeError for a str with non-ASCII characters, and
    # HTTP header values are decoded as latin-1, so a probe can put those on the wire (500
    # instead of 401).
    return hmac.compare_digest(expected.encode(), signature_hex.encode("utf-8", "surrogatepass"))


def wants_announcement(event_type: object) -> bool:
    return event_type in _ANNOUNCEMENT_EVENT_TYPES
