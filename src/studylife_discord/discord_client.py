"""Thin async wrapper around the parts of Discord's REST API this bot actually needs:
posting the session-start/end announcement, and registering slash commands. Deliberately
not a full Discord API client (no discord.py dependency) - Interactions are handled as
plain HTTP requests (main.py), so a persistent Gateway/WebSocket connection is never
needed either.
"""

from __future__ import annotations

import httpx

API_BASE = "https://discord.com/api/v10"


async def post_channel_message(bot_token: str, channel_id: str, content: str) -> None:
    async with httpx.AsyncClient(timeout=10.0) as http:
        response = await http.post(
            f"{API_BASE}/channels/{channel_id}/messages",
            headers={"Authorization": f"Bot {bot_token}"},
            json={"content": content},
        )
        response.raise_for_status()


async def register_global_commands(
    bot_token: str, application_id: str, commands: list[dict[str, object]]
) -> None:
    """PUT (not POST) bulk-overwrites ALL global commands with exactly this list - the
    documented way to register/update Discord slash commands. Global commands can take
    up to an hour to propagate to clients; a guild-scoped registration (not used here)
    would be near-instant, but this bot is meant for one person's own server(s), not
    testing turnaround speed."""
    async with httpx.AsyncClient(timeout=10.0) as http:
        response = await http.put(
            f"{API_BASE}/applications/{application_id}/commands",
            headers={"Authorization": f"Bot {bot_token}"},
            json=commands,
        )
        response.raise_for_status()
