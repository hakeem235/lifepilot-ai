"""Traffic endpoints.

    GET  /api/traffic/next-commute/   → drive estimate to the next located event
    PUT  /api/traffic/origin/         → set the address commutes start from

Read-only with respect to calendar and tasks: nothing here mutates user data
except the user's own explicitly-submitted origin address, so these sit outside
the planner's D10 propose/apply gate by construction.
"""

from __future__ import annotations

from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .service import next_commute
from .settings_store import get_origin, set_origin


class NextCommuteView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(next_commute(request.user, get_origin(request.user)))


class CommuteOriginView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response({"origin": get_origin(request.user)})

    def put(self, request):
        address = request.data.get("origin")
        if not isinstance(address, str):
            return Response({"detail": "origin must be a string"}, status=400)
        return Response({"origin": set_origin(request.user, address)})
