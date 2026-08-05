"""Plan-my-day endpoints (Issue 10.0), split along the D10 propose/apply seam.

    POST /api/planner/plan-day/          → preview only, writes nothing
    POST /api/planner/plan-day/apply/    → writes the user-confirmed placements

The split is the safety property: there is no endpoint that both asks the model
for a plan and writes it. The user must come back with an explicit apply call
carrying the placements they confirmed.
"""

from __future__ import annotations

from datetime import date

from django.utils import timezone
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from . import services


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
