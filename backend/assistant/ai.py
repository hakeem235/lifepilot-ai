"""Shared AI service — single source of truth for chat + daily-brief generation.

Design (docs/ARCHITECTURE.md §3):
- Context bundles, never raw dumps: callers pass a compact, typed context.
- Graceful degradation: every call has a deterministic fallback, so the app is
  fully usable with NO ANTHROPIC_API_KEY set — it returns templated, task-grounded
  text and flags `generated_by="fallback"`. Real Claude output lights up the moment
  the key is provided.
- Model split: a capable model for chat/planning, a cheaper one for routine summaries.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from django.conf import settings


@dataclass
class AIResult:
    text: str
    generated_by: str  # "ai" | "fallback"


@dataclass
class Usage:
    """Per-call token accounting (D12) — logged against the user by the caller."""

    model: str = ""
    input_tokens: int = 0
    output_tokens: int = 0


@dataclass
class StructuredResult:
    """Result of a structured tool-use call (D11).

    `data` is the raw tool input the model produced — still UNTRUSTED. The caller
    must validate every field against the user's own data before any write.
    `data is None` means no usable model output; the caller falls back.
    """

    data: dict | None
    generated_by: str  # "ai" | "fallback"
    usage: Usage = field(default_factory=Usage)


def _client():
    """Return an Anthropic client, or None if no key is configured (fallback mode)."""
    key = settings.ANTHROPIC_API_KEY
    if not key:
        return None
    try:
        from anthropic import Anthropic

        return Anthropic(api_key=key)
    except Exception:
        return None


def _complete(model: str, system: str, user: str, max_tokens: int = 400) -> str | None:
    """One Claude call; returns None on any failure so the caller can fall back."""
    client = _client()
    if client is None:
        return None
    try:
        resp = client.messages.create(
            model=model,
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        parts = [b.text for b in resp.content if getattr(b, "type", None) == "text"]
        text = "".join(parts).strip()
        return text or None
    except Exception:
        return None


# --- Daily brief -----------------------------------------------------------------

def _brief_fallback(ctx: dict) -> str:
    open_count = ctx.get("open_tasks", 0)
    due_today = ctx.get("due_today", 0)
    high = ctx.get("high_priority", 0)
    window = ctx.get("focus_window", "2–4 PM")
    if open_count == 0:
        return f"You're all clear today — no open tasks. A great window to get ahead: {window}."
    bits = [f"{open_count} open task{'s' if open_count != 1 else ''}"]
    if due_today:
        bits.append(f"{due_today} due today")
    if high:
        bits.append(f"{high} high-priority")
    return "You have " + ", ".join(bits) + f". Best focus window: {window}."


def daily_brief(ctx: dict) -> AIResult:
    """Generate the Home AI Daily Brief from a compact task context."""
    system = (
        "You are LifePilot, a concise personal daily assistant. In 1–2 sentences, "
        "summarize the user's day from the given counts and suggest the best focus "
        "window. Warm, direct, no preamble."
    )
    user = (
        f"Open tasks: {ctx.get('open_tasks', 0)}. Due today: {ctx.get('due_today', 0)}. "
        f"High priority: {ctx.get('high_priority', 0)}. "
        f"Suggested focus window: {ctx.get('focus_window', '2–4 PM')}."
    )
    text = _complete(settings.ANTHROPIC_MODEL_SUMMARY, system, user, max_tokens=160)
    if text:
        return AIResult(text=text, generated_by="ai")
    return AIResult(text=_brief_fallback(ctx), generated_by="fallback")


# --- Chat ------------------------------------------------------------------------

def _chat_fallback(message: str, ctx: dict) -> str:
    open_count = ctx.get("open_tasks", 0)
    titles = ctx.get("task_titles", [])
    low = message.lower()
    if any(k in low for k in ("plan", "day", "schedule")):
        if not titles:
            return "Your schedule is clear. Add a task and I'll help you plan around it."
        lines = "\n".join(f"• {t}" for t in titles[:5])
        return f"Here's a simple plan for your {open_count} open task(s):\n{lines}\n\nStart with the highest-priority one during your best focus window."
    if any(k in low for k in ("summary", "summarize", "email")):
        return "Once your email is connected, I'll triage and summarize it here. For now I can help you plan and track tasks."
    if titles:
        return f"You have {open_count} open task(s): {', '.join(titles[:3])}. Ask me to plan your day or prioritize them."
    return "I'm your LifePilot assistant. Add a few tasks and ask me to plan your day, prioritize, or summarize."


def chat(message: str, ctx: dict, history: list[dict] | None = None) -> AIResult:
    """Task-aware conversational reply."""
    system = (
        "You are LifePilot, a proactive personal assistant. You help the user plan "
        "their day, prioritize, and stay on track. Ground answers in the user's task "
        "context. Be concise and practical."
    )
    titles = ctx.get("task_titles", [])
    ctx_line = (
        f"[User context] Open tasks: {ctx.get('open_tasks', 0)}. "
        f"Titles: {', '.join(titles[:10]) or 'none'}."
    )
    user = f"{ctx_line}\n\nUser: {message}"
    text = _complete(settings.ANTHROPIC_MODEL_CHAT, system, user, max_tokens=500)
    if text:
        return AIResult(text=text, generated_by="ai")
    return AIResult(text=_chat_fallback(message, ctx), generated_by="fallback")


# --- Structured tool-use (D11) ---------------------------------------------------

def _tool_call(
    model: str,
    system: str,
    user: str,
    tool: dict,
    max_tokens: int = 1500,
) -> StructuredResult:
    """One Claude call forced through a tool schema; never raises.

    The model cannot answer in prose here — `tool_choice` forces it to emit the
    tool's input object, which is the only thing we read. That is the D11 seam:
    a schema in, a schema out, and a server-side validator between the result and
    any write. Any failure (no key, network, malformed) returns
    `generated_by="fallback"` so the caller uses its deterministic path.
    """
    client = _client()
    if client is None:
        return StructuredResult(data=None, generated_by="fallback")
    try:
        resp = client.messages.create(
            model=model,
            max_tokens=max_tokens,
            system=system,
            tools=[tool],
            tool_choice={"type": "tool", "name": tool["name"]},
            messages=[{"role": "user", "content": user}],
        )
    except Exception:
        return StructuredResult(data=None, generated_by="fallback")

    usage = Usage(
        model=model,
        input_tokens=getattr(resp.usage, "input_tokens", 0) or 0,
        output_tokens=getattr(resp.usage, "output_tokens", 0) or 0,
    )
    for block in resp.content:
        if getattr(block, "type", None) == "tool_use" and block.name == tool["name"]:
            data = block.input
            if isinstance(data, dict):
                return StructuredResult(data=data, generated_by="ai", usage=usage)
    # Well-formed response, no usable tool block — still bill the tokens we spent.
    return StructuredResult(data=None, generated_by="fallback", usage=usage)


PLAN_DAY_TOOL = {
    "name": "propose_schedule",
    "description": (
        "Propose a schedule for the user's unscheduled tasks by placing each one "
        "into a free hour of the day. Every task must either be assigned to a free "
        "hour or listed as overflow with a short reason — never omitted."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "assignments": {
                "type": "array",
                "description": "Task placements. One task per hour; no hour used twice.",
                "items": {
                    "type": "object",
                    "properties": {
                        "task_id": {"type": "string", "description": "id of a task from the list"},
                        "hour": {
                            "type": "integer",
                            "description": "24h clock hour, must be one of the free hours given",
                        },
                    },
                    "required": ["task_id", "hour"],
                },
            },
            "overflow": {
                "type": "array",
                "description": "Tasks that could not be placed, each with a short user-facing reason.",
                "items": {
                    "type": "object",
                    "properties": {
                        "task_id": {"type": "string"},
                        "reason": {"type": "string", "description": "one short sentence"},
                    },
                    "required": ["task_id", "reason"],
                },
            },
        },
        "required": ["assignments", "overflow"],
    },
}


def propose_schedule(ctx: dict) -> StructuredResult:
    """Ask Claude to lay out the day (D13: the capable model does the reasoning).

    `ctx` is a compact bundle for TODAY only (D12) — the candidate tasks, the free
    hours, and the immovable calendar events. The returned data is unvalidated;
    planner.services is responsible for checking it before anything is written.
    """
    system = (
        "You are LifePilot's day planner. You place the user's unscheduled tasks "
        "into free hours of a single day.\n"
        "Hard rules:\n"
        "- You may ONLY use hours listed as free. Calendar events are immovable and "
        "their hours are already excluded — never schedule over one.\n"
        "- At most ONE task per hour. Never double-book.\n"
        "- Schedule the most important work first: urgent+important, then important, "
        "then urgent, then the rest. Respect due dates.\n"
        "- Every task must appear exactly once, in assignments or in overflow. If "
        "there are fewer free hours than tasks, the least important ones overflow.\n"
        "- Prefer earlier hours for demanding work."
    )
    lines = [f"Planning date: {ctx['date']}.", "", "Unscheduled tasks:"]
    for task in ctx["candidates"]:
        due = task["due_date"] or "no due date"
        lines.append(
            f"- id={task['task_id']} | {task['title']} | priority={task['priority']} | due={due}"
        )
    lines.append("")
    lines.append(f"Free hours (24h): {', '.join(str(h) for h in ctx['free_hours']) or 'none'}")
    if ctx.get("events"):
        lines.append("Immovable calendar events (already excluded from free hours):")
        for event in ctx["events"]:
            lines.append(f"- {event}")
    return _tool_call(settings.ANTHROPIC_MODEL_PLAN, system, "\n".join(lines), PLAN_DAY_TOOL)


CAPTURE_TOOL = {
    "name": "capture_task",
    "description": (
        "Extract a single actionable task from the user's message. Always produce a "
        "clean imperative title. Express any date symbolically — never compute a "
        "calendar date yourself, and never guess today's date."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "title": {
                "type": "string",
                "description": (
                    "Short imperative task title, e.g. 'Call the dentist'. Strip filler "
                    "like 'remind me to'. Never include the date or time."
                ),
            },
            "date_mode": {
                "type": "string",
                "enum": ["none", "relative", "weekday", "absolute"],
                "description": (
                    "How the date was expressed. 'none' if no date was mentioned. "
                    "'relative' for today/tomorrow/in N days. 'weekday' for a named day "
                    "of the week. 'absolute' only when a full explicit date was given."
                ),
            },
            "relative_days": {
                "type": "integer",
                "description": "Days from today when date_mode is 'relative': 0=today, 1=tomorrow.",
            },
            "weekday": {
                "type": "string",
                "enum": [
                    "monday",
                    "tuesday",
                    "wednesday",
                    "thursday",
                    "friday",
                    "saturday",
                    "sunday",
                ],
                "description": "The named day, when date_mode is 'weekday'.",
            },
            "weekday_which": {
                "type": "string",
                "enum": ["this", "next"],
                "description": "'next' only when the user explicitly said 'next <day>'.",
            },
            "absolute_date": {
                "type": "string",
                "description": "YYYY-MM-DD, only when date_mode is 'absolute'.",
            },
            "hour": {
                "type": "integer",
                "description": "24-hour clock hour if a time was given, e.g. 2pm → 14. Omit if none.",
            },
            "minute": {"type": "integer", "description": "Minutes past the hour; 0 if unstated."},
            "priority": {
                "type": "string",
                "enum": ["high", "medium", "low"],
                "description": (
                    "'high' only for explicit urgency words (urgent, ASAP, critical, "
                    "important). Default 'medium'."
                ),
            },
            "notes": {
                "type": "string",
                "description": "Any leftover detail worth keeping. Empty string if none.",
            },
        },
        "required": ["title", "date_mode", "priority"],
    },
}


def parse_capture(message: str) -> StructuredResult:
    """Turn free text into a structured task draft (D13: the cheap model).

    Bounded structured extraction — no task context is sent, because the model's
    only job is reading THIS sentence. The returned draft is unvalidated: the
    caller resolves the symbolic date server-side and validates every field.
    """
    system = (
        "You extract one task from a short message the user typed into their planner.\n"
        "- Produce a clean imperative title with filler removed.\n"
        "- You do NOT know today's date. Never output a computed date. Describe the "
        "date symbolically and the server will resolve it.\n"
        "- Only set a time if the user gave one.\n"
        "- Only set priority 'high' if the user signalled urgency.\n"
        "- If the message is just a bare thing to do, that is fine: title only, "
        "date_mode 'none'."
    )
    return _tool_call(
        settings.ANTHROPIC_MODEL_SUMMARY, system, message, CAPTURE_TOOL, max_tokens=600
    )


# --- Daily review (Issue 10.2) ---------------------------------------------------

def _review_fallback(done: list[str], slipped: list[str]) -> str:
    total = len(done) + len(slipped)
    if total == 0:
        return "Nothing was on today's plan. A clean slate for tomorrow."
    if not slipped:
        return f"You finished all {len(done)} task{'s' if len(done) != 1 else ''} today. Strong day."
    if not done:
        return (
            f"{len(slipped)} task{'s' if len(slipped) != 1 else ''} didn't get done today. "
            "Roll them forward and start fresh."
        )
    return (
        f"You completed {len(done)} of {total} tasks today. "
        f"{len(slipped)} slipped — they can move to tomorrow."
    )


def daily_review(done: list[str], slipped: list[str]) -> AIResult:
    """The end-of-day summary sentence (D13: the capable model).

    Prose only, and display-only: nothing is parsed out of this text and no field
    is derived from it. The reschedule proposal that sits next to it in the UI is
    computed deterministically, not read out of this string — which is what keeps
    a chatty model from ever moving a task.
    """
    system = (
        "You are LifePilot writing a user's end-of-day review. In 1–2 sentences: "
        "acknowledge what they finished, name what slipped without judgement, and "
        "point at tomorrow. Warm, direct, specific, no preamble, no bullet points."
    )
    user = (
        f"Completed today ({len(done)}): {', '.join(done[:5]) or 'nothing'}.\n"
        f"Still open ({len(slipped)}): {', '.join(slipped[:5]) or 'nothing'}."
    )
    text = _complete(settings.ANTHROPIC_MODEL_PLAN, system, user, max_tokens=200)
    if text:
        return AIResult(text=text, generated_by="ai")
    return AIResult(text=_review_fallback(done, slipped), generated_by="fallback")
