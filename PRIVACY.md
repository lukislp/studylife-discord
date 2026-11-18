# Privacy

This bot connects one StudyAtrium account to a Discord application. This page says what it
stores and where data goes. It is based on the code in this repository.

## What the bot stores

Nothing in a database. The bot has no database and keeps no message history.

- Configuration lives in the operator's environment (`.env`): the Discord public key, bot
  token and application id, the target channel id, the URL of the StudyAtrium instance, the
  webhook signing secret and **one** StudyAtrium API key.
- The bot is single-user by design: that one API key belongs to the StudyAtrium account that
  ran the login script (`studylife_discord.login`) once. Every slash command acts on that
  account, regardless of which Discord user sends it. Discord users are not linked to
  StudyAtrium accounts and their Discord ids are not stored.
- The bot only writes a log line at startup when the API key is missing. It does not log
  commands, notes or webhook payloads.

## What passes through Discord

Slash command replies (course counts, timer state, study time, sessions, goals, programs,
note titles from a search) are sent to Discord as normal channel messages. They are **not**
ephemeral, so everyone who can see the channel can read them. Focus timer announcements
(`timer.started` / `timer.ended`, with the course name) are posted to the configured channel
through Discord's REST API. Note text you give to `/notiz-erstellen` is sent to Discord as
part of your command and is stored in your StudyAtrium notes. Discord processes all of this
under its own terms and privacy policy; the bot cannot change that. Use it only in channels
whose audience may see your study data.

## What the bot reads from StudyAtrium

With the scopes granted at login (course catalog, timer state, session history, goals, study
programs, notes search, create notes), only in response to a command or a webhook event.
Nothing is fetched on a schedule.

## How long it is kept

The bot itself keeps nothing beyond the configuration above. The API key stays in `.env`
until the operator removes it. Revoke it in StudyAtrium (account settings) to stop the bot
from acting on the account.

## Account deletion

There is no purge endpoint because there is no per-user data stored in the bot. Deleting your
StudyAtrium account revokes the API key, after which the bot can no longer read anything.
Messages already posted to Discord stay there; delete them in Discord.

## Contact

The bot is run by the operator of the StudyAtrium instance it is connected to. Requests about
your data go to that operator. Security issues: see [SECURITY.md](SECURITY.md).
