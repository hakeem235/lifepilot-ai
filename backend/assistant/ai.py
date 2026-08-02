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

from dataclasses import dataclass

from django.conf import settings


@dataclass
class AIResult:
    text: str
    generated_by: str  # "ai" | "fallback"


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
