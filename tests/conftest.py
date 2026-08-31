"""Shared test setup and fixtures.

Env vars are set at import time, before anything from studylife_discord is imported -
config.Settings (and main.get_settings, which is @lru_cache'd) reads them once at
construction time, so they must exist before the first Settings() call anywhere in the
test session.
"""

from __future__ import annotations

import os

from nacl.signing import SigningKey

# A real Ed25519 keypair, generated once for the whole test session. The private half
# stays only in this module (SIGNING_KEY) so tests can sign requests the way Discord
# itself would; only the public half is handed to the app, via DISCORD_PUBLIC_KEY, the
# same way the Discord Developer Portal's General Information page does.
SIGNING_KEY = SigningKey.generate()
PUBLIC_KEY_HEX = SIGNING_KEY.verify_key.encode().hex()

os.environ["DISCORD_PUBLIC_KEY"] = PUBLIC_KEY_HEX
os.environ["DISCORD_BOT_TOKEN"] = "test-bot-token"
os.environ["DISCORD_APPLICATION_ID"] = "1234567890"
os.environ["DISCORD_ANNOUNCE_CHANNEL_ID"] = "9876543210"
os.environ["STUDYLIFE_BASE_URL"] = "https://studylife.example.com"
os.environ["STUDYLIFE_API_KEY"] = "test-studylife-api-key"
os.environ["STUDYLIFE_WEBHOOK_SECRET"] = "test-webhook-secret"


def sign(timestamp: str, body: bytes) -> str:
    """Sign a request body exactly the way Discord signs interactions, so tests can
    build valid X-Signature-Ed25519 headers."""
    signed = SIGNING_KEY.sign(timestamp.encode() + body)
    return signed.signature.hex()
