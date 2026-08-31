"""A duck-typed fake of StudyLifeClient for tests. commands.py only type-hints the
StudyLifeClient parameter - it never isinstance-checks it - so a plain object exposing
the same async methods works fine and keeps tests free of real HTTP.
"""

from __future__ import annotations

from studylife_discord.studylife_client import StudyLifeApiError


class FakeClient:
    def __init__(
        self,
        *,
        courses: list[dict[str, object]] | None = None,
        timer_state: dict[str, object] | None = None,
        session_history: list[dict[str, object]] | None = None,
        all_sessions: list[dict[str, object]] | None = None,
        course_goals: list[dict[str, object]] | None = None,
        study_programs: list[dict[str, object]] | None = None,
        program_details: dict[int, dict[str, object]] | None = None,
        search_results: list[dict[str, object]] | None = None,
        notes: list[dict[str, object]] | None = None,
        create_note_result: dict[str, object] | None = None,
        session_by_id: dict[int, dict[str, object]] | None = None,
        raise_on: set[str] | None = None,
    ) -> None:
        self.calls: list[tuple[object, ...]] = []
        self.courses = courses if courses is not None else []
        self.timer_state = timer_state if timer_state is not None else {"isRunning": False}
        self.session_history = session_history if session_history is not None else []
        self.all_sessions = all_sessions if all_sessions is not None else []
        self.course_goals = course_goals if course_goals is not None else []
        self.study_programs = study_programs if study_programs is not None else []
        self.program_details = program_details if program_details is not None else {}
        self.search_results = search_results if search_results is not None else []
        self.notes = notes if notes is not None else []
        self.create_note_result = create_note_result if create_note_result is not None else {}
        self.session_by_id = session_by_id if session_by_id is not None else {}
        self._raise_on = raise_on if raise_on is not None else set()

    def _maybe_raise(self, method: str) -> None:
        if method in self._raise_on:
            raise StudyLifeApiError(500, "boom")

    async def aclose(self) -> None:
        """No-op so a FakeClient can also stand in for app.state.studylife_client
        during main.py's lifespan shutdown."""

    async def list_courses(self) -> list[dict[str, object]]:
        self.calls.append(("list_courses",))
        self._maybe_raise("list_courses")
        return self.courses

    async def get_timer_state(self) -> dict[str, object]:
        self.calls.append(("get_timer_state",))
        self._maybe_raise("get_timer_state")
        return self.timer_state

    async def get_session_history(self, days: int | None = None) -> list[dict[str, object]]:
        self.calls.append(("get_session_history", days))
        self._maybe_raise("get_session_history")
        return self.session_history

    async def list_all_sessions(self) -> list[dict[str, object]]:
        self.calls.append(("list_all_sessions",))
        self._maybe_raise("list_all_sessions")
        return self.all_sessions

    async def get_session(self, session_id: int) -> dict[str, object] | None:
        self.calls.append(("get_session", session_id))
        self._maybe_raise("get_session")
        return self.session_by_id.get(session_id)

    async def list_course_goals(self) -> list[dict[str, object]]:
        self.calls.append(("list_course_goals",))
        self._maybe_raise("list_course_goals")
        return self.course_goals

    async def list_study_programs(self) -> list[dict[str, object]]:
        self.calls.append(("list_study_programs",))
        self._maybe_raise("list_study_programs")
        return self.study_programs

    async def get_study_program(self, program_id: int) -> dict[str, object]:
        self.calls.append(("get_study_program", program_id))
        self._maybe_raise("get_study_program")
        return self.program_details[program_id]

    async def search_notes(self, query: str) -> list[dict[str, object]]:
        self.calls.append(("search_notes", query))
        self._maybe_raise("search_notes")
        return self.search_results

    async def list_notes(self) -> list[dict[str, object]]:
        self.calls.append(("list_notes",))
        self._maybe_raise("list_notes")
        return self.notes

    async def create_note(self, title: str, content: str) -> dict[str, object]:
        self.calls.append(("create_note", title, content))
        self._maybe_raise("create_note")
        return self.create_note_result
