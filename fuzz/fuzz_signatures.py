"""Atheris fuzz harness for the request-signature checks on the two public endpoints.

Contract under test: verify_signature() (Discord's Ed25519 header check) and
verify_webhook_signature() (StudyLife's HMAC header check) take attacker-controlled header
strings and a raw body. They must answer True or False and never raise - an exception would
turn an unauthenticated probe into a 500 instead of a 401 - and a correctly signed request
must always verify while a tampered one must not.

Run locally (Linux, needs the atheris wheel):
    uv sync --frozen --group fuzz
    uv run python fuzz/fuzz_signatures.py -max_total_time=60
CI runs the same harness for a short, fixed time budget (see .github/workflows/ci.yml).
"""

from __future__ import annotations

import hashlib
import hmac
import sys

import atheris
from nacl.signing import SigningKey

from studylife_discord.verify import verify_signature
from studylife_discord.webhooks import verify_webhook_signature, wants_announcement


def test_one_input(data: bytes) -> None:
    fdp = atheris.FuzzedDataProvider(data)

    # Arbitrary header values: only a boolean answer is acceptable.
    public_key = fdp.ConsumeUnicodeNoSurrogates(80)
    signature = fdp.ConsumeUnicodeNoSurrogates(140)
    timestamp = fdp.ConsumeUnicodeNoSurrogates(24)
    body = fdp.ConsumeBytes(256)
    if not isinstance(verify_signature(public_key, signature, timestamp, body), bool):
        raise AssertionError("verify_signature() did not return a bool")

    # Header values arrive latin-1 decoded, so non-ASCII text is a normal probe.
    secret = fdp.ConsumeUnicodeNoSurrogates(32)
    header = fdp.ConsumeUnicodeNoSurrogates(80)
    if not isinstance(verify_webhook_signature(secret, header, body), bool):
        raise AssertionError("verify_webhook_signature() did not return a bool")

    # A correctly signed request verifies; flipping one body byte breaks it.
    key = SigningKey(fdp.ConsumeBytes(32).ljust(32, b"\0"))
    public_hex = key.verify_key.encode().hex()
    signed = key.sign(timestamp.encode() + body).signature.hex()
    if not verify_signature(public_hex, signed, timestamp, body):
        raise AssertionError("a correctly signed interaction was rejected")
    if verify_signature(public_hex, signed, timestamp, body + b"\0"):
        raise AssertionError("a tampered interaction was accepted")

    digest = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    if not verify_webhook_signature(secret, digest, body):
        raise AssertionError("a correctly signed webhook was rejected")
    if verify_webhook_signature(secret, digest, body + b"\0"):
        raise AssertionError("a tampered webhook was accepted")

    wants_announcement(fdp.ConsumeUnicodeNoSurrogates(16))


if __name__ == "__main__":
    # instrument_all() instead of instrument_imports(): the package is loaded through uv's
    # editable-install loader, which the import hook does not see (no coverage feedback).
    atheris.instrument_all()
    atheris.Setup(sys.argv, test_one_input)
    atheris.Fuzz()
