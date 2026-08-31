from __future__ import annotations

from datetime import datetime, timedelta

from fakes import FakeClient
from studylife_discord import commands
from studylife_discord.commands import (
    _format_duration,
    _pluralize,
    dispatch,
    handle_fortschritt,
    handle_kurse,
    handle_lernzeit,
    handle_lernziele,
    handle_naechste_session,
    handle_notiz_erstellen,
    handle_notizen_anzahl,
    handle_notizen_suche,
    handle_sessions,
    handle_studiengaenge,
    handle_timer,
)


def _iso(dt: datetime) -> str:
    return dt.isoformat()


def _session(hours_ago_start: float, hours_ago_end: float, course_name: str = "Mathe") -> dict:
    now = datetime.now()
    return {
        "startTime": _iso(now - timedelta(hours=hours_ago_start)),
        "endTime": _iso(now - timedelta(hours=hours_ago_end)),
        "courseName": course_name,
    }


# ---------------------------------------------------------------------------
# _pluralize / _format_duration
# ---------------------------------------------------------------------------


def test_pluralize_singular() -> None:
    assert _pluralize(1, "Kurs", "Kurse") == "1 Kurs"


def test_pluralize_plural() -> None:
    assert _pluralize(2, "Kurs", "Kurse") == "2 Kurse"


def test_pluralize_zero_uses_plural() -> None:
    assert _pluralize(0, "Kurs", "Kurse") == "0 Kurse"


def test_format_duration_minutes_only() -> None:
    assert _format_duration(45) == "45 Minuten"


def test_format_duration_one_minute() -> None:
    assert _format_duration(1) == "1 Minute"


def test_format_duration_whole_hours() -> None:
    assert _format_duration(120) == "2 Stunden"


def test_format_duration_hours_and_minutes() -> None:
    assert _format_duration(90) == "1 Stunde und 30 Minuten"


# ---------------------------------------------------------------------------
# handle_kurse
# ---------------------------------------------------------------------------


async def test_handle_kurse_zero() -> None:
    client = FakeClient(courses=[])

    result = await handle_kurse(client, {})

    assert result == "Du hast aktuell keine Kurse in StudyLife angelegt."


async def test_handle_kurse_one_uses_singular() -> None:
    client = FakeClient(courses=[{"id": 1}])

    result = await handle_kurse(client, {})

    assert "1 Kurs " in result


async def test_handle_kurse_multiple_uses_plural() -> None:
    client = FakeClient(courses=[{"id": 1}, {"id": 2}])

    result = await handle_kurse(client, {})

    assert "2 Kurse" in result


# ---------------------------------------------------------------------------
# handle_timer
# ---------------------------------------------------------------------------


async def test_handle_timer_not_running() -> None:
    client = FakeClient(timer_state={"isRunning": False})

    result = await handle_timer(client, {})

    assert result == "Gerade läuft kein Fokus-Timer."


async def test_handle_timer_running_on_break() -> None:
    client = FakeClient(timer_state={"isRunning": True, "isBreak": True})

    result = await handle_timer(client, {})

    assert "Pause" in result


async def test_handle_timer_running_not_on_break() -> None:
    client = FakeClient(timer_state={"isRunning": True, "isBreak": False})

    result = await handle_timer(client, {})

    assert result == "Dein Fokus-Timer läuft gerade."


# ---------------------------------------------------------------------------
# handle_lernzeit
# ---------------------------------------------------------------------------


async def test_handle_lernzeit_today_zero_minutes() -> None:
    client = FakeClient(session_history=[])

    result = await handle_lernzeit(client, {"zeitraum": "today"})

    assert result == "Du hast heute noch nicht gelernt."


async def test_handle_lernzeit_today_counts_only_todays_session() -> None:
    today_session = _session(2, 1)  # one hour, ending an hour ago
    three_days_ago_session = _session(3 * 24 + 2, 3 * 24 + 1)
    client = FakeClient(session_history=[today_session, three_days_ago_session])

    result = await handle_lernzeit(client, {"zeitraum": "today"})

    assert result == "Du hast heute 1 Stunde gelernt."


async def test_handle_lernzeit_hours_and_minutes_formatting() -> None:
    session = _session(2, 0.5)  # 1.5 hours
    client = FakeClient(session_history=[session])

    result = await handle_lernzeit(client, {"zeitraum": "today"})

    assert result == "Du hast heute 1 Stunde und 30 Minuten gelernt."


async def test_handle_lernzeit_week_includes_session_from_three_days_ago() -> None:
    three_days_ago_session = _session(3 * 24 + 2, 3 * 24 + 1)  # one hour session
    client = FakeClient(session_history=[three_days_ago_session])

    result = await handle_lernzeit(client, {"zeitraum": "week"})

    assert result == "Du hast diese Woche 1 Stunde gelernt."


async def test_handle_lernzeit_last_week_excludes_session_from_today() -> None:
    """Regression guard: a session within the current week must NOT count towards
    "letzte Woche" - the exact bug the sibling Alexa skill had to fix."""
    today_session = _session(2, 1)
    client = FakeClient(session_history=[today_session])

    result = await handle_lernzeit(client, {"zeitraum": "last_week"})

    assert result == "Du hast letzte Woche noch nicht gelernt."


async def test_handle_lernzeit_last_week_includes_session_from_ten_days_ago() -> None:
    ten_days_ago_session = _session(10 * 24 + 2, 10 * 24 + 1)  # one hour session
    client = FakeClient(session_history=[ten_days_ago_session])

    result = await handle_lernzeit(client, {"zeitraum": "last_week"})

    assert result == "Du hast letzte Woche 1 Stunde gelernt."


# ---------------------------------------------------------------------------
# handle_sessions
# ---------------------------------------------------------------------------


async def test_handle_sessions_empty() -> None:
    client = FakeClient(session_history=[])

    result = await handle_sessions(client, {})

    assert result == "Du hast in den letzten sieben Tagen keine Lernsessions gehabt."


async def test_handle_sessions_non_empty() -> None:
    sessions = [
        _session(2, 1, course_name="Mathe"),
        _session(3, 2, course_name="Physik"),
    ]
    client = FakeClient(session_history=sessions)

    result = await handle_sessions(client, {})

    assert "2 Lernsessions" in result
    assert "Mathe" in result
    assert "Physik" in result


# ---------------------------------------------------------------------------
# handle_naechste_session
# ---------------------------------------------------------------------------


async def test_handle_naechste_session_none_upcoming() -> None:
    client = FakeClient(all_sessions=[])

    result = await handle_naechste_session(client, {})

    assert result == "Du hast aktuell keine geplante Lernsession in StudyLife."


async def test_handle_naechste_session_one_upcoming() -> None:
    start = datetime.now() + timedelta(days=2)
    session = {"startTime": _iso(start), "courseName": "Datenbanken"}
    client = FakeClient(all_sessions=[session])

    result = await handle_naechste_session(client, {})

    assert f"{start:%d.%m.}" in result
    assert f"{start:%H:%M}" in result
    assert "Datenbanken" in result


# ---------------------------------------------------------------------------
# handle_lernziele
# ---------------------------------------------------------------------------


async def test_handle_lernziele_zero() -> None:
    client = FakeClient(course_goals=[])

    result = await handle_lernziele(client, {})

    assert result == "Du hast aktuell keine Lernziele in StudyLife angelegt."


async def test_handle_lernziele_mixed_completed_and_open() -> None:
    goals = [
        {"completedAt": None},
        {"completedAt": "2026-01-01T00:00:00"},
        {"completedAt": None},
    ]
    client = FakeClient(course_goals=goals)

    result = await handle_lernziele(client, {})

    assert "3 Lernziele" in result
    assert "sind 2 noch offen" in result


# ---------------------------------------------------------------------------
# handle_studiengaenge
# ---------------------------------------------------------------------------


async def test_handle_studiengaenge_zero() -> None:
    client = FakeClient(study_programs=[])

    result = await handle_studiengaenge(client, {})

    assert result == "Du hast aktuell keinen Studiengang in StudyLife angelegt."


async def test_handle_studiengaenge_multiple() -> None:
    programs = [{"name": "Informatik"}, {"name": "Mathematik"}]
    client = FakeClient(study_programs=programs)

    result = await handle_studiengaenge(client, {})

    assert "2 Studiengänge" in result
    assert "Informatik" in result
    assert "Mathematik" in result


# ---------------------------------------------------------------------------
# handle_fortschritt
# ---------------------------------------------------------------------------


async def test_handle_fortschritt_program_not_found() -> None:
    client = FakeClient(study_programs=[{"id": 1, "name": "Informatik"}])

    result = await handle_fortschritt(client, {"studiengang": "Nichtvorhanden"})

    assert result == "Ich konnte keinen Studiengang namens Nichtvorhanden finden."


async def test_handle_fortschritt_found_via_exact_substring() -> None:
    programs = [{"id": 1, "name": "Informatik (B.Sc.)"}]
    detail = {"name": "Informatik (B.Sc.)", "groupEctsQuotas": {}}
    client = FakeClient(study_programs=programs, program_details={1: detail})

    result = await handle_fortschritt(client, {"studiengang": "Informatik"})

    assert "Informatik (B.Sc.)" in result


async def test_handle_fortschritt_found_via_fuzzy_match() -> None:
    programs = [{"id": 1, "name": "Applied Artificial Intelligence"}]
    detail = {"name": "Applied Artificial Intelligence", "groupEctsQuotas": {}}
    client = FakeClient(study_programs=programs, program_details={1: detail})

    result = await handle_fortschritt(client, {"studiengang": "Applied Artifical Intelligence"})

    assert "Applied Artificial Intelligence" in result


async def test_handle_fortschritt_builtin_program_has_no_progress_data() -> None:
    programs = [{"id": None, "name": "Eigene Kurse"}]
    client = FakeClient(study_programs=programs)

    result = await handle_fortschritt(client, {"studiengang": "Eigene Kurse"})

    assert "keine Fortschrittsdaten verfügbar" in result
    assert not any(call[0] == "get_study_program" for call in client.calls)


async def test_handle_fortschritt_zero_ects_quotas() -> None:
    programs = [{"id": 1, "name": "Informatik"}]
    detail = {"name": "Informatik", "groupEctsQuotas": {}}
    client = FakeClient(study_programs=programs, program_details={1: detail})

    result = await handle_fortschritt(client, {"studiengang": "Informatik"})

    assert result == "Für Informatik sind aktuell keine ECTS-Quoten hinterlegt."


async def test_handle_fortschritt_computes_completed_ects() -> None:
    programs = [{"id": 1, "name": "Informatik"}]
    detail = {
        "name": "Informatik",
        "groupEctsQuotas": {"Pflicht": 30, "Wahlpflicht": 20},
    }
    courses = [
        {"id": 1, "ects": 5, "group": "Pflicht"},
        {"id": 2, "ects": 10, "group": "Wahlpflicht"},
        {"id": 3, "ects": 8, "group": "Pflicht"},  # not completed
        {"id": 4, "ects": 7, "group": "Sonstiges"},  # completed, but not in any quota
    ]
    goals = [
        {"courseId": 1, "completedAt": "2026-01-01T00:00:00"},
        {"courseId": 2, "completedAt": "2026-01-02T00:00:00"},
        {"courseId": 4, "completedAt": "2026-01-03T00:00:00"},
    ]
    client = FakeClient(
        study_programs=programs, program_details={1: detail}, courses=courses, course_goals=goals
    )

    result = await handle_fortschritt(client, {"studiengang": "Informatik"})

    # completed: course 1 (5) + course 2 (10) = 15; total quota: 30 + 20 = 50
    assert result == "Du hast 15 von 50 ECTS in Informatik abgeschlossen."


# ---------------------------------------------------------------------------
# handle_notizen_suche
# ---------------------------------------------------------------------------


async def test_handle_notizen_suche_no_results() -> None:
    client = FakeClient(search_results=[])

    result = await handle_notizen_suche(client, {"suchbegriff": "Quantenphysik"})

    assert result == "Ich habe keine Notizen zu Quantenphysik gefunden."


async def test_handle_notizen_suche_some_results() -> None:
    notes = [{"title": "Vorlesung 1"}, {"title": "Vorlesung 2"}]
    client = FakeClient(search_results=notes)

    result = await handle_notizen_suche(client, {"suchbegriff": "Vorlesung"})

    assert "Vorlesung 1" in result
    assert "Vorlesung 2" in result


# ---------------------------------------------------------------------------
# handle_notizen_anzahl
# ---------------------------------------------------------------------------


async def test_handle_notizen_anzahl_zero() -> None:
    client = FakeClient(notes=[])

    result = await handle_notizen_anzahl(client, {})

    assert result == "Du hast aktuell keine Notizen in StudyLife."


async def test_handle_notizen_anzahl_some() -> None:
    client = FakeClient(notes=[{"id": 1}, {"id": 2}, {"id": 3}])

    result = await handle_notizen_anzahl(client, {})

    assert "3 Notizen" in result


# ---------------------------------------------------------------------------
# handle_notiz_erstellen
# ---------------------------------------------------------------------------


async def test_handle_notiz_erstellen() -> None:
    client = FakeClient()

    result = await handle_notiz_erstellen(client, {"text": "Nicht vergessen: Klausur lernen"})

    assert result == "Notiz gespeichert."
    create_calls = [call for call in client.calls if call[0] == "create_note"]
    assert len(create_calls) == 1
    _, title, content = create_calls[0]
    assert f"{datetime.now():%d.%m.%Y}" in title
    assert content == "Nicht vergessen: Klausur lernen"


# ---------------------------------------------------------------------------
# dispatch
# ---------------------------------------------------------------------------


async def test_dispatch_unknown_command_does_not_call_client() -> None:
    client = FakeClient()

    result = await dispatch("unbekannter-befehl", {}, client)

    assert result == "Diesen Befehl kenne ich nicht."
    assert client.calls == []


async def test_dispatch_catches_studylife_api_error() -> None:
    client = FakeClient(raise_on={"list_courses"})

    result = await dispatch("kurse", {}, client)

    assert result == commands.UNREACHABLE_MESSAGE
