from __future__ import annotations

from conftest import PUBLIC_KEY_HEX, sign
from studylife_discord.verify import verify_signature

TIMESTAMP = "1700000000"
BODY = b'{"type":1}'


def test_valid_signature_is_accepted() -> None:
    signature = sign(TIMESTAMP, BODY)

    assert verify_signature(PUBLIC_KEY_HEX, signature, TIMESTAMP, BODY) is True


def test_tampered_body_is_rejected() -> None:
    signature = sign(TIMESTAMP, BODY)

    assert verify_signature(PUBLIC_KEY_HEX, signature, TIMESTAMP, b'{"type":2}') is False


def test_wrong_timestamp_is_rejected() -> None:
    signature = sign(TIMESTAMP, BODY)

    assert verify_signature(PUBLIC_KEY_HEX, signature, "1700000001", BODY) is False


def test_garbage_signature_hex_is_rejected_without_crashing() -> None:
    assert verify_signature(PUBLIC_KEY_HEX, "not-hex", TIMESTAMP, BODY) is False


def test_garbage_public_key_hex_is_rejected_without_crashing() -> None:
    signature = sign(TIMESTAMP, BODY)

    assert verify_signature("not-hex", signature, TIMESTAMP, BODY) is False


def test_signature_of_wrong_length_is_rejected_without_crashing() -> None:
    assert verify_signature(PUBLIC_KEY_HEX, "ab", TIMESTAMP, BODY) is False
