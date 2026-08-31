"""Slash command definitions (for registration, see discord_client.register_global_commands)
and their handlers. Each handler returns the plain text response content - main.py wraps
it into Discord's CHANNEL_MESSAGE_WITH_SOURCE response shape.

Deliberately flat top-level commands rather than Discord's subcommand-grouping feature,
matching studylife-alexa's own flat intent list - simpler to implement/test for v1, and
Discord's real enum CHOICES (unlike Alexa's fuzzy-matched custom slot values) already
avoid the "letzte Woche" vs "diese Woche" ambiguity that needed extra work there.
"""

from __future__ import annotations

import difflib
from datetime import datetime, timedelta

from studylife_discord.studylife_client import StudyLifeApiError, StudyLifeClient

_TIME_PERIOD_CHOICES = [
    {"name": "Heute", "value": "today"},
    {"name": "Diese Woche", "value": "week"},
    {"name": "Letzte Woche", "value": "last_week"},
    {"name": "Diesen Monat", "value": "month"},
    {"name": "Letzten Monat", "value": "last_month"},
]

# (fetch_days, window_start_days_ago, window_end_days_ago, label) - see
# studylife-alexa's handlers.py _period_for_time_period for the identical reasoning
# (the API's own "days" filter only looks backward from now, so "letzte Woche"/"letzten
# Monat" fetch a wider window and get filtered down client-side).
_TIME_PERIODS: dict[str, tuple[int, int, int, str]] = {
    "today": (1, 0, 0, "heute"),
    "week": (7, 0, 6, "diese Woche"),
    "last_week": (14, 7, 13, "letzte Woche"),
    "month": (30, 0, 29, "diesen Monat"),
    "last_month": (60, 30, 59, "letzten Monat"),
}

COMMAND_DEFINITIONS: list[dict[str, object]] = [
    {"name": "kurse", "description": "Zeigt deine Kurse in StudyLife.", "type": 1},
    {"name": "timer", "description": "Zeigt den Status deines Fokus-Timers.", "type": 1},
    {
        "name": "lernzeit",
        "description": "Zeigt deine Lernzeit für einen Zeitraum.",
        "type": 1,
        "options": [
            {
                "name": "zeitraum",
                "description": "Der Zeitraum",
                "type": 3,
                "required": True,
                "choices": _TIME_PERIOD_CHOICES,
            }
        ],
    },
    {"name": "sessions", "description": "Zeigt deine letzten Lernsessions.", "type": 1},
    {
        "name": "naechste-session",
        "description": "Zeigt deine nächste geplante Lernsession.",
        "type": 1,
    },
    {"name": "lernziele", "description": "Zeigt deine Lernziele.", "type": 1},
    {"name": "studiengaenge", "description": "Zeigt deine Studiengänge.", "type": 1},
    {
        "name": "fortschritt",
        "description": "Zeigt deinen ECTS-Fortschritt in einem Studiengang.",
        "type": 1,
        "options": [
            {
                "name": "studiengang",
                "description": "Name des Studiengangs",
                "type": 3,
                "required": True,
            }
        ],
    },
    {
        "name": "notizen-suche",
        "description": "Durchsucht deine Notizen.",
        "type": 1,
        "options": [
            {
                "name": "suchbegriff",
                "description": "Wonach gesucht werden soll",
                "type": 3,
                "required": True,
            }
        ],
    },
    {"name": "notizen-anzahl", "description": "Zeigt, wie viele Notizen du hast.", "type": 1},
    {
        "name": "notiz-erstellen",
        "description": "Erstellt eine neue Notiz.",
        "type": 1,
        "options": [
            {"name": "text", "description": "Der Inhalt der Notiz", "type": 3, "required": True}
        ],
    },
]


def _pluralize(count: int, singular: str, plural: str) -> str:
    return f"{count} {singular if count == 1 else plural}"


def _filter_sessions_by_window(
    sessions: list[dict[str, object]], start_days_ago: int, end_days_ago: int
) -> list[dict[str, object]]:
    now = datetime.now()
    window_start = now - timedelta(days=end_days_ago + 1)
    window_end = now - timedelta(days=start_days_ago)
    filtered = []
    for session in sessions:
        start = session.get("startTime")
        if not isinstance(start, str):
            continue
        try:
            start_dt = datetime.fromisoformat(start)
        except ValueError:
            continue
        if window_start <= start_dt <= window_end:
            filtered.append(session)
    return filtered


def _sum_session_minutes(sessions: list[dict[str, object]]) -> int:
    total_seconds = 0.0
    for session in sessions:
        start, end = session.get("startTime"), session.get("endTime")
        if not isinstance(start, str) or not isinstance(end, str):
            continue
        try:
            total_seconds += (
                datetime.fromisoformat(end) - datetime.fromisoformat(start)
            ).total_seconds()
        except ValueError:
            continue
    return int(total_seconds // 60)


def _format_duration(total_minutes: int) -> str:
    if total_minutes < 60:
        return _pluralize(total_minutes, "Minute", "Minuten")
    hours, minutes = divmod(total_minutes, 60)
    if minutes == 0:
        return _pluralize(hours, "Stunde", "Stunden")
    return (
        f"{_pluralize(hours, 'Stunde', 'Stunden')} und {_pluralize(minutes, 'Minute', 'Minuten')}"
    )


def _find_program_by_name(
    programs: list[dict[str, object]], query: str
) -> dict[str, object] | None:
    query_lower = query.strip().lower()
    if not query_lower:
        return None
    names_lower = [str(p.get("name", "")).lower() for p in programs]
    for program, name_lower in zip(programs, names_lower, strict=True):
        if query_lower in name_lower or name_lower in query_lower:
            return program
    close_matches = difflib.get_close_matches(query_lower, names_lower, n=1, cutoff=0.75)
    if close_matches:
        return programs[names_lower.index(close_matches[0])]
    return None


def _program_progress(
    detail: dict[str, object], courses: list[dict[str, object]], goals: list[dict[str, object]]
) -> tuple[int, int]:
    quotas = detail.get("groupEctsQuotas")
    if not isinstance(quotas, dict):
        return 0, 0
    total_ects = sum(int(v) for v in quotas.values() if isinstance(v, int | float))
    completed_course_ids = {
        g.get("courseId") for g in goals if g.get("completedAt") and g.get("courseId") is not None
    }
    completed_ects = 0
    for course in courses:
        ects = course.get("ects")
        if (
            course.get("id") in completed_course_ids
            and course.get("group") in quotas
            and isinstance(ects, int | float)
        ):
            completed_ects += int(ects)
    return completed_ects, total_ects


def _next_upcoming_session(
    sessions: list[dict[str, object]],
) -> tuple[datetime, str | None] | None:
    now = datetime.now()
    upcoming: list[tuple[datetime, str | None]] = []
    for session in sessions:
        start = session.get("startTime")
        if not isinstance(start, str):
            continue
        try:
            start_dt = datetime.fromisoformat(start)
        except ValueError:
            continue
        if start_dt > now:
            course_name = session.get("courseName")
            upcoming.append((start_dt, str(course_name) if course_name else None))
    return min(upcoming, key=lambda pair: pair[0]) if upcoming else None


async def handle_kurse(client: StudyLifeClient, options: dict[str, str]) -> str:
    courses = await client.list_courses()
    if not courses:
        return "Du hast aktuell keine Kurse in StudyLife angelegt."
    return f"Du hast aktuell {_pluralize(len(courses), 'Kurs', 'Kurse')} in StudyLife."


async def handle_timer(client: StudyLifeClient, options: dict[str, str]) -> str:
    state = await client.get_timer_state()
    if not state.get("isRunning"):
        return "Gerade läuft kein Fokus-Timer."
    if state.get("isBreak"):
        return "Dein Fokus-Timer läuft, du bist gerade in einer Pause."
    return "Dein Fokus-Timer läuft gerade."


async def handle_lernzeit(client: StudyLifeClient, options: dict[str, str]) -> str:
    fetch_days, start_days_ago, end_days_ago, label = _TIME_PERIODS[
        options.get("zeitraum", "today")
    ]
    sessions = await client.get_session_history(fetch_days)
    sessions = _filter_sessions_by_window(sessions, start_days_ago, end_days_ago)
    minutes = _sum_session_minutes(sessions)
    if minutes == 0:
        return f"Du hast {label} noch nicht gelernt."
    return f"Du hast {label} {_format_duration(minutes)} gelernt."


async def handle_sessions(client: StudyLifeClient, options: dict[str, str]) -> str:
    sessions = await client.get_session_history(days=7)
    if not sessions:
        return "Du hast in den letzten sieben Tagen keine Lernsessions gehabt."
    names = ", ".join(str(s.get("courseName", "-")) for s in sessions[:5] if s.get("courseName"))
    count_text = _pluralize(len(sessions), "Lernsession", "Lernsessions")
    text = f"In den letzten sieben Tagen hattest du {count_text}"
    return text + (f", zuletzt in: {names}." if names else ".")


async def handle_naechste_session(client: StudyLifeClient, options: dict[str, str]) -> str:
    sessions = await client.list_all_sessions()
    upcoming = _next_upcoming_session(sessions)
    if upcoming is None:
        return "Du hast aktuell keine geplante Lernsession in StudyLife."
    start_dt, course_name = upcoming
    text = f"Deine nächste Lernsession ist am {start_dt:%d.%m.} um {start_dt:%H:%M} Uhr"
    return text + (f" für {course_name}." if course_name else ".")


async def handle_lernziele(client: StudyLifeClient, options: dict[str, str]) -> str:
    goals = await client.list_course_goals()
    if not goals:
        return "Du hast aktuell keine Lernziele in StudyLife angelegt."
    open_goals = sum(1 for g in goals if not g.get("completedAt"))
    verb = "ist" if open_goals == 1 else "sind"
    count_text = _pluralize(len(goals), "Lernziel", "Lernziele")
    return f"Du hast {count_text} in StudyLife, davon {verb} {open_goals} noch offen."


async def handle_studiengaenge(client: StudyLifeClient, options: dict[str, str]) -> str:
    programs = await client.list_study_programs()
    if not programs:
        return "Du hast aktuell keinen Studiengang in StudyLife angelegt."
    names = ", ".join(str(p.get("name", "-")) for p in programs)
    return (
        f"Du hast {_pluralize(len(programs), 'Studiengang', 'Studiengänge')} in StudyLife: {names}."
    )


async def handle_fortschritt(client: StudyLifeClient, options: dict[str, str]) -> str:
    query = options.get("studiengang", "")
    programs = await client.list_study_programs()
    program = _find_program_by_name(programs, query)
    if program is None:
        return f"Ich konnte keinen Studiengang namens {query} finden."
    if program.get("id") is None:
        program_name = str(program.get("name", query))
        return (
            f"Für den eingebauten Studiengang {program_name} sind über die "
            "Schnittstelle leider keine Fortschrittsdaten verfügbar."
        )

    detail = await client.get_study_program(int(program["id"]))
    courses = await client.list_courses()
    goals = await client.list_course_goals()
    completed_ects, total_ects = _program_progress(detail, courses, goals)
    program_name = str(detail.get("name", query))
    if total_ects == 0:
        return f"Für {program_name} sind aktuell keine ECTS-Quoten hinterlegt."
    return f"Du hast {completed_ects} von {total_ects} ECTS in {program_name} abgeschlossen."


async def handle_notizen_suche(client: StudyLifeClient, options: dict[str, str]) -> str:
    query = options.get("suchbegriff", "")
    notes = await client.search_notes(query)
    if not notes:
        return f"Ich habe keine Notizen zu {query} gefunden."
    titles = ", ".join(str(n.get("title", "-")) for n in notes[:5])
    count_text = _pluralize(len(notes), "Notiz", "Notizen")
    return f"Ich habe {count_text} zu {query} gefunden, unter anderem: {titles}."


async def handle_notizen_anzahl(client: StudyLifeClient, options: dict[str, str]) -> str:
    notes = await client.list_notes()
    if not notes:
        return "Du hast aktuell keine Notizen in StudyLife."
    return f"Du hast insgesamt {_pluralize(len(notes), 'Notiz', 'Notizen')} in StudyLife."


async def handle_notiz_erstellen(client: StudyLifeClient, options: dict[str, str]) -> str:
    content = options.get("text", "")
    title = f"Discord-Notiz vom {datetime.now():%d.%m.%Y}"
    await client.create_note(title, content)
    return "Notiz gespeichert."


HANDLERS = {
    "kurse": handle_kurse,
    "timer": handle_timer,
    "lernzeit": handle_lernzeit,
    "sessions": handle_sessions,
    "naechste-session": handle_naechste_session,
    "lernziele": handle_lernziele,
    "studiengaenge": handle_studiengaenge,
    "fortschritt": handle_fortschritt,
    "notizen-suche": handle_notizen_suche,
    "notizen-anzahl": handle_notizen_anzahl,
    "notiz-erstellen": handle_notiz_erstellen,
}

UNREACHABLE_MESSAGE = "StudyLife konnte gerade nicht erreicht werden. Versuch es später noch mal."


async def dispatch(command_name: str, options: dict[str, str], client: StudyLifeClient) -> str:
    handler = HANDLERS.get(command_name)
    if handler is None:
        return "Diesen Befehl kenne ich nicht."
    try:
        return await handler(client, options)
    except StudyLifeApiError:
        return UNREACHABLE_MESSAGE
