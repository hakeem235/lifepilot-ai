"""Planner AI endpoints, split along the D10 propose/apply seam.

    POST /api/planner/plan-day/          → preview only, writes nothing
    POST /api/planner/plan-day/apply/    → writes the user-confirmed placements
    POST /api/planner/capture/           → preview only, creates no Task
    POST /api/planner/capture/apply/     → creates the confirmed task
    GET  /api/planner/review/            → evening review, writes nothing
    POST /api/planner/review/apply/      → rolls confirmed slipped tasks forward

The split is the safety property: there is no endpoint that both asks the model
for a plan and writes it. The user must come back with an explicit apply call
carrying the placements they confirmed.
"""

from __future__ import annotations

from datetime import date, timedelta

from django.utils import timezone
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from tasks.serializers import TaskSerializer

from . import capture, review, services


def _requested_day(request) -> date | None:
    """The day being planned; defaults to today. None means the input was bad."""
    raw = request.data.get("date") or request.query_params.get("date")
    if not raw:
        return timezone.localdate()
    try:
        return date.fromisoformat(str(raw))
    except ValueError:
        return None


class PlanDayView(APIView):
    """Propose a schedule. Read-only with respect to the user's tasks."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        day = _requested_day(request)
        if day is None:
            return Response({"detail": "date must be YYYY-MM-DD."}, status=400)
        return Response(services.propose_day_plan(request.user, day))


class PlanDayApplyView(APIView):
    """Apply the confirmed placements. The only path that writes a proposed plan."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        day = _requested_day(request)
        if day is None:
            return Response({"detail": "date must be YYYY-MM-DD."}, status=400)
        assignments = request.data.get("assignments")
        if not isinstance(assignments, list):
            return Response({"detail": "assignments must be a list."}, status=400)
        result = services.apply_day_plan(request.user, day, assignments)
        return Response(result)


class CaptureView(APIView):
    """Parse free text into a task draft. Creates no Task (D10)."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        message = (request.data.get("message") or "").strip()
        if not message:
            return Response({"detail": "message is required."}, status=400)
        if len(message) > 1000:
            return Response({"detail": "message is too long."}, status=400)
        return Response(capture.propose_capture(request.user, message))


class CaptureApplyView(APIView):
    """Create the confirmed task. The only path in capture that writes."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        draft = request.data.get("draft")
        task, warning = capture.apply_capture(request.user, draft)
        if task is None:
            return Response({"detail": "draft is missing a usable title."}, status=400)
        return Response({"task": TaskSerializer(task).data, "warning": warning}, status=201)


class DailyReviewView(APIView):
    """The evening review for a day. Writes nothing (D10)."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        day = _requested_day(request)
        if day is None:
            return Response({"detail": "date must be YYYY-MM-DD."}, status=400)
        return Response(review.propose_review(request.user, day))


class DailyReviewApplyView(APIView):
    """Roll the confirmed slipped tasks forward.

    Delegates to the same validated writer the auto-scheduler uses, so the
    reschedule inherits its ownership check, conflict re-validation and
    `previous`-state capture rather than reimplementing them.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        raw = request.data.get("reschedule_date") or request.data.get("date")
        try:
            target = date.fromisoformat(str(raw)) if raw else timezone.localdate() + timedelta(days=1)
        except ValueError:
            return Response({"detail": "reschedule_date must be YYYY-MM-DD."}, status=400)
        moves = request.data.get("moves")
        if not isinstance(moves, list):
            return Response({"detail": "moves must be a list."}, status=400)
        return Response(services.apply_day_plan(request.user, target, moves))
