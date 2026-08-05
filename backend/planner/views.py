"""Planner AI endpoints, split along the D10 propose/apply seam.

    POST /api/planner/plan-day/          → preview only, writes nothing
    POST /api/planner/plan-day/apply/    → writes the user-confirmed placements
    POST /api/planner/capture/           → preview only, creates no Task
    POST /api/planner/capture/apply/     → creates the confirmed task
    GET  /api/planner/review/            → evening review, writes nothing
    POST /api/planner/review/apply/      → rolls confirmed slipped tasks forward

    POST /api/planner/undo/              → reverses a previously applied change

The split is the safety property: there is no endpoint that both asks the model
for a plan and writes it. The user must come back with an explicit apply call
carrying the placements they confirmed.

Each view inherits from ProposalEndpoint or ApplyEndpoint (see gate.py, Issue
10.3), which declares which side of that line it sits on. The gate audit walks
this URLconf and holds every endpoint to its declaration.
"""

from __future__ import annotations

from datetime import date, timedelta

from django.utils import timezone
from rest_framework.response import Response

from tasks.serializers import TaskSerializer

from . import capture, review, services, undo
from .gate import ApplyEndpoint, ProposalEndpoint


def _requested_day(request) -> date | None:
    """The day being planned; defaults to today. None means the input was bad."""
    raw = request.data.get("date") or request.query_params.get("date")
    if not raw:
        return timezone.localdate()
    try:
        return date.fromisoformat(str(raw))
    except ValueError:
        return None


class PlanDayView(ProposalEndpoint):
    """Propose a schedule. Read-only with respect to the user's tasks."""


    def post(self, request):
        day = _requested_day(request)
        if day is None:
            return Response({"detail": "date must be YYYY-MM-DD."}, status=400)
        return Response(services.propose_day_plan(request.user, day))


class PlanDayApplyView(ApplyEndpoint):
    """Apply the confirmed placements. The only path that writes a proposed plan."""


    def post(self, request):
        day = _requested_day(request)
        if day is None:
            return Response({"detail": "date must be YYYY-MM-DD."}, status=400)
        assignments = request.data.get("assignments")
        if not isinstance(assignments, list):
            return Response({"detail": "assignments must be a list."}, status=400)
        result = services.apply_day_plan(request.user, day, assignments)
        return Response(result)


class CaptureView(ProposalEndpoint):
    """Parse free text into a task draft. Creates no Task (D10)."""


    def post(self, request):
        message = (request.data.get("message") or "").strip()
        if not message:
            return Response({"detail": "message is required."}, status=400)
        if len(message) > 1000:
            return Response({"detail": "message is too long."}, status=400)
        return Response(capture.propose_capture(request.user, message))


class CaptureApplyView(ApplyEndpoint):
    """Create the confirmed task. The only path in capture that writes."""


    def post(self, request):
        draft = request.data.get("draft")
        task, warning = capture.apply_capture(request.user, draft)
        if task is None:
            return Response({"detail": "draft is missing a usable title."}, status=400)
        return Response({"task": TaskSerializer(task).data, "warning": warning}, status=201)


class DailyReviewView(ProposalEndpoint):
    """The evening review for a day. Writes nothing (D10)."""


    def get(self, request):
        day = _requested_day(request)
        if day is None:
            return Response({"detail": "date must be YYYY-MM-DD."}, status=400)
        return Response(review.propose_review(request.user, day))


class DailyReviewApplyView(ApplyEndpoint):
    """Roll the confirmed slipped tasks forward.

    Delegates to the same validated writer the auto-scheduler uses, so the
    reschedule inherits its ownership check, conflict re-validation and
    `previous`-state capture rather than reimplementing them.
    """


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


class UndoView(ApplyEndpoint):
    """Reverse a previously applied AI change.

    A write, and gated as one — but the user has already confirmed the intent by
    tapping undo, so there is no separate preview step.
    """

    def post(self, request):
        result = undo.undo_apply(
            request.user,
            request.data.get("previous", []),
            request.data.get("created_task_ids", []),
        )
        return Response(result)
