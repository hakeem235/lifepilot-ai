"""Natural-language capture (Issue 10.1) — free text in, confirmable task draft out.

Same seam as "Plan my day": propose builds a preview, apply writes. Nothing the
model produces becomes a Task without the user confirming it (D10).

The division of labour is the D11 rule taken literally:

    Claude   reads the sentence and emits a typed draft with a *symbolic* date
    server   resolves that symbol against the user's timezone, validates every
             field, sanitizes the text, and only then writes

There is no regex in this file and no date parsing of free text anywhere. If the
model is unavailable the fallback keeps the title and drops the date entirely —
deliberately, because a guessed date is worse than no date.
"""

from __future__ import annotations

from datetime import date, time

from assistant import ai
from assistant.models import AIUsage
from tasks.models import Task

from .dates import resolve_date, resolve_time, user_today

TITLE_MAX = 255
NOTES_MAX = 2000
PRIORITIES = {"high", "medium", "low"}


def sanitize_text(value: object, limit: int) -> str:
    """Strip NUL and control characters before text reaches DRF/Postgres.

    Postgres text columns reject NUL bytes outright and DRF's CharField chokes on
    control characters, which shows up as a mystifying 400 on an otherwise valid
    capture ([PHASE-6] learning). Model output is text from outside the system, so
    it gets the same treatment as OCR extraction did.
    """
    if not isinstance(value, str):
        return ""
    cleaned = "".join(ch for ch in value if ch == "\n" or ch >= " ")
    return cleaned.strip()[:limit]


def build_draft(data: dict | None, today: date, raw_message: str) -> dict | None:
    """Validate an untrusted capture draft into concrete Task fields.

    Returns None when there is no usable title — the one field with no safe
    default. Everything else degrades to a sensible absence rather than failing
    the whole capture, so "buy milk" and a richly specified reminder both work.
    """
    if not isinstance(data, dict):
        return None
    title = sanitize_text(data.get("title"), TITLE_MAX)
    if not title:
        return None

    priority = data.get("priority")
    if priority not in PRIORITIES:
        priority = Task.Priority.MEDIUM

    resolved_date = resolve_date(data, today)
    resolved_time = resolve_time(data) if resolved_date else None

    return {
        "title": title,
        "notes": sanitize_text(data.get("notes"), NOTES_MAX),
        "priority": priority,
        # A date always sets the due date so the task surfaces in Today/Upcoming.
        "due_date": resolved_date.isoformat() if resolved_date else None,
        # A date AND a time additionally place it on the timeline; a date alone
        # would otherwise land on a day with no slot and render nowhere (the 9.0
        # timeline draws by scheduled_time), so it stays in the tray instead.
        "scheduled_date": resolved_date.isoformat() if resolved_date and resolved_time else None,
        "scheduled_time": resolved_time.strftime("%H:%M") if resolved_time else None,
        "source": Task.Source.AI,
        "original_text": sanitize_text(raw_message, NOTES_MAX),
    }


def fallback_draft(message: str) -> dict | None:
    """Title-only capture when live Claude is unavailable.

    Deliberately dateless: extracting "tomorrow 2pm" without a model would mean
    regex-parsing free text, which D11 forbids precisely because it silently
    produces wrong dates. A title the user can date themselves is the honest
    degradation.
    """
    title = sanitize_text(message, TITLE_MAX)
    if not title:
        return None
    return {
        "title": title,
        "notes": "",
        "priority": Task.Priority.MEDIUM,
        "due_date": None,
        "scheduled_date": None,
        "scheduled_time": None,
        "source": Task.Source.AI,
        "original_text": title,
    }


def propose_capture(user, message: str) -> dict:
    """Parse free text into a confirmable task draft. Writes no Task (D10)."""
    result = ai.parse_capture(message)
    generated_by = "fallback"
    draft = None

    if result.generated_by == "ai":
        draft = build_draft(result.data, user_today(user.timezone), message)
        if draft is not None:
            generated_by = "ai"
    if draft is None:
        draft = fallback_draft(message)

    AIUsage.objects.create(
        user=user,
        purpose=AIUsage.Purpose.CAPTURE,
        model=result.usage.model,
        generated_by=generated_by,
        input_tokens=result.usage.input_tokens,
        output_tokens=result.usage.output_tokens,
    )

    return {
        "kind": "capture",
        "generated_by": generated_by,
        "draft": draft,
        # True when the model was reachable but produced nothing we could use —
        # the UI says "I couldn't read a task out of that" rather than inventing one.
        "understood": draft is not None,
        "slot_conflict": _slot_taken(user, draft) if draft else False,
    }


def _slot_taken(user, draft: dict) -> bool:
    """Whether the drafted timeline slot is already occupied (D15)."""
    if not draft.get("scheduled_date") or not draft.get("scheduled_time"):
        return False
    hour = int(draft["scheduled_time"][:2])
    return Task.objects.filter(
        user=user,
        scheduled_date=draft["scheduled_date"],
        scheduled_time__hour=hour,
    ).exists()


def apply_capture(user, draft: dict) -> tuple[Task | None, str | None]:
    """Create the confirmed task. The only path in capture that writes.

    Re-validates rather than trusting the payload — the draft has been through the
    client and may have been edited there. Returns (task, warning); a warning of
    "slot_taken" means the task was created but left in the tray rather than
    double-booked (D15), never silently dropped.
    """
    if not isinstance(draft, dict):
        return None, "invalid"
    title = sanitize_text(draft.get("title"), TITLE_MAX)
    if not title:
        return None, "invalid"

    priority = draft.get("priority")
    if priority not in PRIORITIES:
        priority = Task.Priority.MEDIUM

    due_date = _as_date(draft.get("due_date"))
    scheduled_date = _as_date(draft.get("scheduled_date"))
    scheduled_time = _as_time(draft.get("scheduled_time"))

    warning = None
    if scheduled_date and scheduled_time:
        clash = Task.objects.filter(
            user=user, scheduled_date=scheduled_date, scheduled_time__hour=scheduled_time.hour
        ).exists()
        if clash:
            # Keep the task, drop the placement: the user still gets their reminder,
            # and resolves the slot on the timeline.
            scheduled_date, scheduled_time = None, None
            warning = "slot_taken"
    else:
        scheduled_date, scheduled_time = None, None

    task = Task.objects.create(
        user=user,
        title=title,
        notes=sanitize_text(draft.get("notes"), NOTES_MAX),
        priority=priority,
        due_date=due_date,
        scheduled_date=scheduled_date,
        scheduled_time=scheduled_time,
        source=Task.Source.AI,
    )
    return task, warning


def _as_date(value: object) -> date | None:
    if not isinstance(value, str):
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def _as_time(value: object) -> time | None:
    if not isinstance(value, str):
        return None
    try:
        parts = [int(p) for p in value.split(":")[:2]]
    except ValueError:
        return None
    if len(parts) < 2 or not (0 <= parts[0] <= 23 and 0 <= parts[1] <= 59):
        return None
    return time(hour=parts[0], minute=parts[1])
