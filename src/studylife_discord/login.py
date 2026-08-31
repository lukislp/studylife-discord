"""One-time browser login (`python -m studylife_discord.login <instance-url>`).

Ported from studylife-cli's own login.py (same generic connect flow,
identity-contract-v1 SS2: /connect/client/{client_id} + POST /api/auth/assertion-exchange) -
this bot has no per-Discord-user account linking the way studylife-alexa needs (Alexa's
account-linking protocol requires it); it only ever acts on the single StudyLife account
that ran this script once, so a plain loopback login writing STUDYLIFE_API_KEY into .env
is all that's needed.
"""

from __future__ import annotations

import hmac
import secrets
import sys
import webbrowser
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urlparse

import httpx

CLIENT_ID = "studylife-discord"
CANDIDATE_PORTS = (8765, 8766, 8767, 8768)
CALLBACK_TIMEOUT_SECONDS = 300.0


class LoginError(Exception):
    pass


@dataclass
class CallbackResult:
    state: str
    assertion: str


def _parse_callback_query(query_string: str) -> CallbackResult:
    query = parse_qs(query_string)
    return CallbackResult(
        state=query.get("state", [""])[0],
        assertion=query.get("assertion", [""])[0],
    )


_CALLBACK_PAGE = """<!doctype html>
<html lang="en">
<head><meta charset="utf-8"><title>studylife-discord login</title></head>
<body style="font-family: sans-serif; text-align: center; padding-top: 3rem;">
<p>Login complete &mdash; you can close this tab and return to the terminal.</p>
</body>
</html>
"""


class _CallbackState:
    def __init__(self) -> None:
        self.result: CallbackResult | None = None


def _make_handler(state: _CallbackState) -> type[BaseHTTPRequestHandler]:
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, format: str, *args: object) -> None:
            pass

        def do_GET(self) -> None:
            parsed = urlparse(self.path)
            if parsed.path != "/callback":
                self.send_response(404)
                self.end_headers()
                return

            state.result = _parse_callback_query(parsed.query)

            body = _CALLBACK_PAGE.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    return Handler


class _LoopbackHTTPServer(HTTPServer):
    # See studylife-cli's own login.py for why this must be False on Windows.
    allow_reuse_address = False


class _CallbackHTTPServer:
    def __init__(self, port: int) -> None:
        self._state = _CallbackState()
        self._server = _LoopbackHTTPServer(("127.0.0.1", port), _make_handler(self._state))

    @property
    def port(self) -> int:
        return int(self._server.server_address[1])

    def wait_for_callback(self, timeout_seconds: float) -> CallbackResult | None:
        self._server.timeout = timeout_seconds
        self._server.handle_request()
        self._server.server_close()
        return self._state.result


def _bind_first_free_port(candidates: tuple[int, ...]) -> _CallbackHTTPServer:
    last_error: OSError | None = None
    for port in candidates:
        try:
            return _CallbackHTTPServer(port)
        except OSError as exc:
            last_error = exc
            continue
    raise LoginError(
        f"None of the candidate ports {list(candidates)} are free on 127.0.0.1."
    ) from last_error


def _exchange_assertion(base_url: str, assertion: str) -> str:
    try:
        response = httpx.post(
            f"{base_url}/api/auth/assertion-exchange",
            json={"clientId": CLIENT_ID, "assertion": assertion},
            timeout=10.0,
        )
    except httpx.HTTPError as exc:
        raise LoginError(f"Could not reach StudyLife: {exc}") from exc

    if response.status_code != 200:
        raise LoginError(
            f"StudyLife rejected the login ({response.status_code}): {response.text.strip()}"
        )
    try:
        return str(response.json()["apiKey"])
    except (KeyError, TypeError, ValueError) as exc:
        raise LoginError("StudyLife returned an unexpected response shape.") from exc


def run_login(instance_url: str) -> str:
    base_url = instance_url.rstrip("/")
    state_token = secrets.token_urlsafe(32)

    callback_server = _bind_first_free_port(CANDIDATE_PORTS)
    redirect_uri = f"http://127.0.0.1:{callback_server.port}/callback"
    connect_url = (
        f"{base_url}/connect/client/{CLIENT_ID}?"
        f"{urlencode({'redirect_uri': redirect_uri, 'state': state_token})}"
    )

    print(f"Opening your browser to log in to StudyLife:\n  {connect_url}")
    webbrowser.open(connect_url)

    result = callback_server.wait_for_callback(CALLBACK_TIMEOUT_SECONDS)
    if result is None:
        raise LoginError(
            f"Timed out after {int(CALLBACK_TIMEOUT_SECONDS)}s waiting for the callback - "
            f"is '{CLIENT_ID}' registered via studylife-developers with a matching "
            "redirect URI yet?"
        )
    if not hmac.compare_digest(result.state, state_token):
        raise LoginError("State mismatch - please run this command again.")
    if not result.assertion:
        raise LoginError("No assertion received - the connection may have been denied.")

    return _exchange_assertion(base_url, result.assertion)


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: python -m studylife_discord.login <instance-url> [--env-file .env]")
        return 1

    instance_url = sys.argv[1]
    env_file = Path(".env")
    if "--env-file" in sys.argv:
        env_file = Path(sys.argv[sys.argv.index("--env-file") + 1])

    try:
        api_key = run_login(instance_url)
    except LoginError as exc:
        print(f"Login failed: {exc}", file=sys.stderr)
        return 1

    existing = env_file.read_text(encoding="utf-8") if env_file.exists() else ""
    lines = [line for line in existing.splitlines() if not line.startswith("STUDYLIFE_API_KEY=")]
    lines.append(f"STUDYLIFE_API_KEY={api_key}")
    env_file.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"Login successful - STUDYLIFE_API_KEY written to {env_file}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
