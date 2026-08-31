from pydantic import AnyHttpUrl
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration, loaded from environment variables / .env."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # From the Discord Developer Portal's General Information page - used to verify the
    # Ed25519 signature on every incoming interaction (verify.py). Hex-encoded, as
    # Discord displays it.
    discord_public_key: str

    # Bot token (Bot tab) - Authorization: Bot <token> header for every outgoing Discord
    # REST call (posting the announcement message, registering slash commands).
    discord_bot_token: str

    # Application ID (General Information page) - needed to build the slash-command
    # registration URL (PUT /applications/{id}/commands).
    discord_application_id: str

    # Channel to post "session started/ended" announcements to. Optional: leave unset to
    # disable announcements entirely (slash commands still work without it).
    discord_announce_channel_id: str | None = None

    # This single person's StudyLife instance and API key - no per-user account linking
    # like studylife-alexa needs, since this bot only ever acts on one StudyLife account
    # (obtained once via login.py, mirroring studylife-cli/studylife-mcp's own login
    # flow), not on behalf of arbitrary Discord users.
    studylife_base_url: AnyHttpUrl
    studylife_api_key: str | None = None

    # HMAC-SHA256 secret StudyLife signs each webhook delivery with (X-StudyLife-
    # Webhook-Signature header) - the same value entered when registering this bot's
    # webhook via WebhooksProxy.Create (client.py's register_webhook). Required only for
    # the webhook receiver (main.py's /webhooks/studylife route), not for slash commands.
    studylife_webhook_secret: str | None = None
