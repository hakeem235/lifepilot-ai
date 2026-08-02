"""Core views — health check and API root.

The health endpoint is intentionally unauthenticated and dependency-light so CI,
Render health checks, and the mobile app's connectivity probe can all hit it
before auth (Issue 8.1) or the AI proxy (Issue 8.3) exist.
"""

from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView


class HealthView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        return Response({"status": "ok", "service": "lifepilot-ai"})
