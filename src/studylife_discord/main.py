"""FastAPI app wiring Discord's HTTP Interactions endpoint and StudyLife's webhook push
endpoint - both stateless request/response, no Gateway/WebSocket connection needed.
"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from functools import lru_cache

from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import JSONResponse

from studylife_discord.commands import dispatch
from studylife_discord.config import Settings
from studylife_discord.discord_client import post_channel_message
from studylife_discord.studylife_client import StudyLifeClient
from studylife_discord.verify import verify_signature
from studylife_discord.webhooks import verify_webhook_signature, wants_announcement

logger = logging.getLogger("studylife_discord")

_DISCORD_PING = 1
_DISCORD_APPLICATION_COMMAND = 2
_RESPONSE_PONG = 1
_RESPONSE_CHANNEL_MESSAGE = 4


@lru_cache
def get_settings() -> Settings:
    return Settings()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    if settings.studylife_api_key:
        app.state.studylife_client = StudyLifeClient(
            str(settings.studylife_base_url), settings.studylife_api_key
        )
    else:
        app.state.studylife_client = None
        logger.warning("STUDYLIFE_API_KEY not set - slash commands will report an error.")
    yield
    if app.state.studylife_client is not None:
        await app.state.studylife_client.aclose()


app = FastAPI(lifespan=lifespan)


def _extract_options(interaction_data: dict[str, object]) -> dict[str, str]:
    raw_options = interaction_data.get("options")
    if not isinstance(raw_options, list):
        return {}
    options: dict[str, str] = {}
    for option in raw_options:
        if isinstance(option, dict) and "name" in option:
            options[str(option["name"])] = str(option.get("value", ""))
    return options


@app.post("/interactions")
async def interactions(
    request: Request,
    x_signature_ed25519: str = Header(...),
    x_signature_timestamp: str = Header(...),
) -> JSONResponse:
    body = await request.body()
    settings = get_settings()
    if not verify_signature(
        settings.discord_public_key, x_signature_ed25519, x_signature_timestamp, body
    ):
        raise HTTPException(status_code=401, detail="Invalid request signature.")

    interaction = await request.json()
    interaction_type = interaction.get("type")

    if interaction_type == _DISCORD_PING:
        return JSONResponse({"type": _RESPONSE_PONG})

    if interaction_type == _DISCORD_APPLICATION_COMMAND:
        data = interaction.get("data", {})
        command_name = str(data.get("name", ""))
        options = _extract_options(data)

        client: StudyLifeClient | None = request.app.state.studylife_client
        if client is None:
            content = "Der Bot ist noch nicht mit StudyLife verbunden."
        else:
            content = await dispatch(command_name, options, client)

        return JSONResponse({"type": _RESPONSE_CHANNEL_MESSAGE, "data": {"content": content}})

    raise HTTPException(status_code=400, detail="Unsupported interaction type.")


@app.get("/healthz")
async def healthz() -> dict[str, bool]:
    return {"ok": True}


@app.post("/webhooks/studylife")
async def studylife_webhook(
    request: Request,
    x_studylife_webhook_signature: str = Header(...),
) -> JSONResponse:
    body = await request.body()
    settings = get_settings()
    if not settings.studylife_webhook_secret:
        raise HTTPException(status_code=503, detail="Webhook secret not configured.")
    if not verify_webhook_signature(
        settings.studylife_webhook_secret, x_studylife_webhook_signature, body
    ):
        raise HTTPException(status_code=401, detail="Invalid webhook signature.")

    event = await request.json()
    event_type = event.get("event_type")
    payload = event.get("payload") or {}

    if wants_announcement(event_type) and settings.discord_announce_channel_id:
        client: StudyLifeClient | None = request.app.state.studylife_client
        session_id = payload.get("sessionId")
        course_name = None
        if client is not None and isinstance(session_id, int):
            session = await client.get_session(session_id)
            if session is not None:
                course_name = session.get("courseName")

        if event_type == "timer.started":
            content = "Fokus-Timer gestartet" + (f" für {course_name}." if course_name else ".")
        else:
            content = "Fokus-Timer beendet" + (f" für {course_name}." if course_name else ".")

        await post_channel_message(
            settings.discord_bot_token, settings.discord_announce_channel_id, content
        )

    return JSONResponse({"status": "ok"})
