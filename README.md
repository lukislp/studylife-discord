# studylife-discord

[![CI](https://github.com/lukislp/studylife-discord/actions/workflows/ci.yml/badge.svg)](https://github.com/lukislp/studylife-discord/actions/workflows/ci.yml) [![OpenSSF Scorecard](https://img.shields.io/ossf-scorecard/github.com/lukislp/studylife-discord?label=openssf+scorecard&style=flat)](https://scorecard.dev/viewer/?uri=github.com/lukislp/studylife-discord) [![CodeQL](https://github.com/lukislp/studylife-discord/actions/workflows/github-code-scanning/codeql/badge.svg)](https://github.com/lukislp/studylife-discord/security/code-scanning)
[![Release](https://img.shields.io/github/v/release/lukislp/studylife-discord)](https://github.com/lukislp/studylife-discord/releases)
[![License: AGPL-3.0](https://img.shields.io/github/license/lukislp/studylife-discord)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.12-3776AB)](https://www.python.org/)

Discord bot for [StudyLife](https://github.com/lukislp/studylife): slash commands for
courses/timer/study time/study programs/notes, plus automatic focus-timer start/end
channel announcements driven by StudyLife's own webhook system.

Single-user by design - unlike [studylife-alexa](https://github.com/lukislp/studylife-alexa),
there's no per-Discord-user account linking. One StudyLife account logs in once
(`login.py`) and the bot acts on that account for every command.

## Status

- `/kurse` - "wie viele Kurse habe ich"
- `/timer` - Fokus-Timer-Status (read-only)
- `/lernzeit zeitraum:<Heute/Diese Woche/Letzte Woche/Diesen Monat/Letzten Monat>` -
  a real Discord choice enum, so unlike Alexa's fuzzy-matched custom slot this can't
  confuse "letzte Woche" with "diese Woche"
- `/sessions` - letzte 7 Tage
- `/naechste-session` - nächste geplante Session (`/api/sessions`, the only endpoint
  that returns future sessions at all)
- `/lernziele` - offene/gesamt Lernziele
- `/studiengaenge` - alle Studiengänge
- `/fortschritt studiengang:<Name>` - ECTS-Fortschritt, derived client-side from
  `Courses` + `CourseGoals` since `StudyPrograms.Get` only returns quotas, not actual
  progress (same approach as studylife-alexa's `ProgramProgressIntent`); the built-in
  program (`id: null`) has no detail endpoint and is reported as such
- `/notizen-suche suchbegriff:<...>`
- `/notizen-anzahl`
- `/notiz-erstellen text:<...>`

Automatic announcements: subscribing to StudyLife's `timer.started`/`timer.ended`
webhook events posts a plain channel message (via Discord's REST API, not a Gateway
Rich Presence - this bot never holds a persistent connection) to
`DISCORD_ANNOUNCE_CHANNEL_ID` whenever the focus timer starts or stops.

Deliberately not exposed via slash command: deleting/editing notes, sessions, or
course goals - same reasoning as studylife-alexa, needs a real confirmation-step design
first.

## Development

```bash
uv sync
cp .env.example .env
uv run python -m studylife_discord.login https://your-studylife-instance   # writes STUDYLIFE_API_KEY into .env
uv run uvicorn studylife_discord.main:app --reload
uv run pytest
uv run ruff check .
uv run ruff format --check .
```

## Setup

1. Create a Discord Application + Bot in the
   [Discord Developer Portal](https://discord.com/developers/applications). Copy its
   **Public Key** (`DISCORD_PUBLIC_KEY`), **Application ID**
   (`DISCORD_APPLICATION_ID`), and generate/copy a **Bot Token** (`DISCORD_BOT_TOKEN`).
   Invite the bot to your server with the `applications.commands` and `bot` (Send
   Messages) scopes.
2. Register `studylife-discord` as an ordinary add-on on your own
   [studylife-developers](https://github.com/lukislp/studylife-developers) instance
   (same generic connect flow as studylife-cli/studylife-alexa): **Client ID**:
   `studylife-discord`, redirect URI `http://127.0.0.1:8765/callback` (through `8768`).
   Scopes: Read the course catalog, Read live timer state, Read session history, Read
   course goals, Read study programs, Search notes, Create notes.
3. Run the login script above once to obtain `STUDYLIFE_API_KEY`.
4. Register the slash commands with Discord (bulk-overwrites all global commands -
   can take up to an hour to propagate):
   ```bash
   uv run python -c "
   import asyncio
   from studylife_discord.commands import COMMAND_DEFINITIONS
   from studylife_discord.discord_client import register_global_commands
   from studylife_discord.config import Settings
   s = Settings()
   asyncio.run(register_global_commands(s.discord_bot_token, s.discord_application_id, COMMAND_DEFINITIONS))
   "
   ```
5. In the Discord Developer Portal's **General Information** page, set
   **Interactions Endpoint URL** to `https://<your-public-url>/interactions` (Discord
   sends a PING immediately and requires a valid signed PONG before saving).
6. To enable announcements, create a webhook via StudyLife pointing at
   `https://<your-public-url>/webhooks/studylife` subscribed to `timer.started` and
   `timer.ended`, and set `STUDYLIFE_WEBHOOK_SECRET` to the secret it gives you plus
   `DISCORD_ANNOUNCE_CHANNEL_ID` to the target channel's ID.

## Deployment

Self-hosted (K3s + Tailscale Funnel), same pattern as
[studylife-alexa](https://github.com/lukislp/studylife-alexa).

## License

AGPL-3.0
