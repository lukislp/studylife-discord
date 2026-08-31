"""Typed async HTTP client for StudyLife's REST API - unlike studylife-alexa's client.py,
everything here can stay async end to end: Discord's HTTP Interactions model (unlike
ask-sdk-core's dispatcher) has no synchronous-callback constraint, so there's no need for
a parallel set of *_sync functions.
"""

from __future__ import annotations

import httpx


class StudyLifeApiError(Exception):
    """Raised for any non-2xx response from StudyLife, carrying the status and body."""

    def __init__(self, status_code: int, body: str) -> None:
        super().__init__(f"StudyLife API returned {status_code}: {body.strip()}")
        self.status_code = status_code
        self.body = body


class StudyLifeClient:
    def __init__(self, base_url: str, api_key: str, timeout: float = 10.0) -> None:
        self._http = httpx.AsyncClient(
            base_url=base_url.rstrip("/"),
            headers={"X-Api-Key": api_key},
            timeout=timeout,
        )

    async def aclose(self) -> None:
        await self._http.aclose()

    async def __aenter__(self) -> StudyLifeClient:
        return self

    async def __aexit__(self, *exc_info: object) -> None:
        await self.aclose()

    async def _request(self, method: str, path: str, **kwargs: object) -> httpx.Response:
        response = await self._http.request(method, path, **kwargs)
        if response.status_code >= 400:
            raise StudyLifeApiError(response.status_code, response.text)
        return response

    async def list_courses(self) -> list[dict[str, object]]:
        return list((await self._request("GET", "/api/courses")).json())

    async def get_timer_state(self) -> dict[str, object]:
        return dict((await self._request("GET", "/api/timerstate")).json())

    async def get_session_history(self, days: int | None = None) -> list[dict[str, object]]:
        params: dict[str, object] = {"days": days} if days is not None else {}
        return list((await self._request("GET", "/api/sessions/history", params=params)).json())

    async def list_all_sessions(self) -> list[dict[str, object]]:
        return list((await self._request("GET", "/api/sessions")).json())

    async def get_session(self, session_id: int) -> dict[str, object] | None:
        for session in await self.list_all_sessions():
            if session.get("id") == session_id:
                return session
        return None

    async def list_course_goals(self) -> list[dict[str, object]]:
        return list((await self._request("GET", "/api/coursegoals")).json())

    async def list_study_programs(self) -> list[dict[str, object]]:
        return list((await self._request("GET", "/api/studyprograms")).json())

    async def get_study_program(self, program_id: int) -> dict[str, object]:
        return dict((await self._request("GET", f"/api/studyprograms/{program_id}")).json())

    async def search_notes(self, query: str) -> list[dict[str, object]]:
        response = await self._request("GET", "/api/notes/search", params={"q": query})
        return list(response.json())

    async def list_notes(self) -> list[dict[str, object]]:
        return list((await self._request("GET", "/api/notes")).json())

    async def create_note(self, title: str, content: str) -> dict[str, object]:
        response = await self._request(
            "POST", "/api/notes", json={"title": title, "content": content}
        )
        return dict(response.json())

    async def create_webhook(self, target_url: str, events: list[str]) -> dict[str, object]:
        response = await self._request(
            "POST", "/api/webhooks", json={"targetUrl": target_url, "events": events}
        )
        return dict(response.json())
