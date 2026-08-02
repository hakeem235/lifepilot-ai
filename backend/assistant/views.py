"""AI endpoints — /api/ai/brief/ (Home) and /api/ai/chat/ (AI Chat).

Both build a compact task context for the authenticated user and delegate to the
shared assistant.ai service, which returns real Claude output or a deterministic
fallback (never errors out on a missing key)."""

from django.utils import timezone
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from tasks.models import Task
from . import ai
from .models import CopilotMessage, DailySummary


def _task_context(user) -> dict:
    today = timezone.localdate()
    open_qs = Task.objects.filter(user=user, status=Task.Status.OPEN)
    return {
        "open_tasks": open_qs.count(),
        "due_today": open_qs.filter(due_date__lte=today).count(),
        "high_priority": open_qs.filter(priority=Task.Priority.HIGH).count(),
        "task_titles": list(open_qs.values_list("title", flat=True)[:10]),
        "focus_window": "2–4 PM",
    }


class BriefView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        ctx = _task_context(request.user)
        result = ai.daily_brief(ctx)
        today = timezone.localdate()
        DailySummary.objects.update_or_create(
            user=request.user,
            date=today,
            defaults={
                "summary_text": result.text,
                "best_focus_window": ctx["focus_window"],
                "task_due_count": ctx["due_today"],
                "generated_by": result.generated_by,
            },
        )
        return Response(
            {
                "summary": result.text,
                "generated_by": result.generated_by,
                "best_focus_window": ctx["focus_window"],
                "open_tasks": ctx["open_tasks"],
                "due_today": ctx["due_today"],
                "high_priority": ctx["high_priority"],
            }
        )


class ChatView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        msgs = CopilotMessage.objects.filter(user=request.user)[:100]
        return Response(
            [{"role": m.role, "content": m.content, "created_at": m.created_at} for m in msgs]
        )

    def post(self, request):
        message = (request.data.get("message") or "").strip()
        if not message:
            return Response({"detail": "message is required."}, status=400)
        ctx = _task_context(request.user)
        CopilotMessage.objects.create(user=request.user, role="user", content=message, context_ref=ctx)
        result = ai.chat(message, ctx)
        CopilotMessage.objects.create(user=request.user, role="assistant", content=result.text)
        return Response({"reply": result.text, "generated_by": result.generated_by})
