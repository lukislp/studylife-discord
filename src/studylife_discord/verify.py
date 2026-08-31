"""Ed25519 signature verification for Discord's HTTP Interactions model - the same
"prove this request actually came from Discord" mechanism Alexa's request-signing
serves in studylife-alexa, using Ed25519 instead of RSA. See
https://discord.com/developers/docs/interactions/receiving-and-responding#security-and-authorization.
"""

from __future__ import annotations

from nacl.exceptions import BadSignatureError
from nacl.signing import VerifyKey


def verify_signature(public_key_hex: str, signature_hex: str, timestamp: str, body: bytes) -> bool:
    try:
        verify_key = VerifyKey(bytes.fromhex(public_key_hex))
        verify_key.verify(timestamp.encode() + body, bytes.fromhex(signature_hex))
    except (BadSignatureError, ValueError):
        return False
    return True
