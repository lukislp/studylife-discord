# Contributing to studylife-discord

Thanks for taking the time. This is a single-maintainer project, so the process is deliberately
small - but it is the same for every change, including the maintainer's own.

## How changes get in

1. Open an issue first for anything bigger than a typo or an obvious bug fix, so the direction can
   be agreed before you spend time on it. Use the templates under `.github/ISSUE_TEMPLATE/`.
2. Fork the repository (or branch, if you have write access) and make your change on a branch.
3. Open a pull request against `main`. The pull-request template asks for what changed and why.
4. `main` is protected: a PR merges only once its required checks are green (`ci.yml`'s `lint`
   and `test` jobs, plus `review / dependency-review` and CodeQL code scanning) and the branch is
   up to date with `main`. Nobody pushes to `main` directly, not even the maintainer.

## What a pull request needs

- **Conventional Commit title.** (`fix:`, `feat:`, `ci:`, `docs:`, ...) Unlike some of this
  account's other repos, semantic-release is already live here: a `fix:`/`feat:` commit on `main`
  drives a real version bump, a `CHANGELOG.md` entry, and a multi-arch, cosign-signed Docker image
  push to `ghcr.io/lukislp/studylife-discord`. Get the type right - `chore:`/`docs:`/`test:` do not
  trigger a release, `fix:`/`feat:` do. If the PR is squash-merged, the squashed commit message -
  usually the PR title - is what ends up in history and what semantic-release parses.
- **Tests for new functionality.** `tests/` covers the FastAPI app end to end with `fakes.py`
  standing in for Discord and StudyLife: `test_commands.py` exercises the slash-command handlers,
  `test_webhooks.py` the `timer.started`/`timer.ended` webhook receiver and its HMAC signature
  check, `test_verify.py` the Ed25519 request-signature verification every Discord interaction goes
  through, and `test_main.py` the FastAPI routes themselves. Add tests alongside the behaviour
  you're changing rather than as an afterthought.
- **No secrets or personal data.** Nothing under `src/` or `tests/` should reference a real
  Discord bot token, StudyLife instance URL, or personal Discord/StudyLife IDs - use a placeholder
  like `https://your-studylife-instance` or `.env.example`'s empty values, the way the existing
  code does.
- **Wire shapes.** `studylife_client.py` talks to the same StudyLife REST API the other
  studylife-* clients do, and reads responses as plain `dict[str, object]` rather than validated
  DTOs. The server silently accepts and ignores unknown JSON field names, and a wrong key on the
  read side just returns `None`/a default instead of raising - so a typo produces a green build and
  a command that quietly reports nothing. Check a field against the server's actual response shape
  before relying on it, don't guess from documentation alone.

## Running things locally

```bash
uv sync --frozen
cp .env.example .env
uv run ruff check .
uv run ruff format --check .
uv run pytest
```

Requires Python 3.12 and [`uv`](https://docs.astral.sh/uv/). `ci.yml`'s `lint` job runs both ruff
commands above (not just `ruff check` - formatting drift fails CI on its own), and `test` runs
`pytest`. A push to `main` that adds a release additionally builds and pushes a signed multi-arch
(amd64 + arm64) Docker image via `Dockerfile` - see `README.md`'s Development/Setup sections for
running the bot itself against a real Discord application and StudyLife instance.

## Security issues

Please do not open a public issue for a vulnerability - use the private reporting path described
in [SECURITY.md](SECURITY.md).
