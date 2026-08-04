"""Google Calendar endpoints (Issue 9.3).

- status / auth-url / events / disconnect are Clerk-authenticated (per-user).
- callback is public (Google's browser redirect hits it) and identifies the user
  via a signed `state`, then verifies the granted scope really includes
  calendar.readonly before marking the account connected (Base44 lesson 3).
"""

import secrets
from datetime import date

import httpx
from django.core import signing
from django.http import HttpResponse
from django.utils.dateparse import parse_date
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from users.models import UserProfile

from . import google, service
from .models import GoogleCalendarConnection, PendingOAuth

STATE_SALT = "gcal.oauth.state"
STATE_MAX_AGE = 600  # seconds


class CalendarStatusView(APIView):
    def get(self, request):
        connected = GoogleCalendarConnection.objects.filter(user=request.user).exists()
        return Response({"configured": google.is_configured(), "connected": connected})


class CalendarAuthURLView(APIView):
    def get(self, request):
        if not google.is_configured():
            return Response(
                {"detail": "Google Calendar is not configured on the server."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        # Single-use nonce recorded server-side and bound into the signed state, so
        # a state can be used at most once and only if it matches a real, recent
        # initiation by this user (replay + CSRF defense).
        nonce = secrets.token_urlsafe(32)
        PendingOAuth.objects.create(user=request.user, nonce=nonce)
        state = signing.dumps({"u": str(request.user.id), "n": nonce}, salt=STATE_SALT)
        return Response({"url": google.build_auth_url(state)})


class CalendarCallbackView(APIView):
    authentication_classes: list = []
    permission_classes = [AllowAny]

    def get(self, request):
        code = request.query_params.get("code")
        state = request.query_params.get("state", "")
        if not code:
            return HttpResponse("Missing authorization code.", status=400)
        try:
            payload = signing.loads(state, salt=STATE_SALT, max_age=STATE_MAX_AGE)
            user_id, nonce = payload["u"], payload["n"]
        except (signing.BadSignature, KeyError, TypeError):
            return HttpResponse("Invalid or expired state.", status=400)

        # Consume the single-use initiation record; reject if missing/stale/mismatched.
        pending = PendingOAuth.objects.filter(nonce=nonce, user_id=user_id).first()
        if pending is None or not pending.is_fresh(STATE_MAX_AGE):
            if pending is not None:
                pending.delete()
            return HttpResponse("Invalid or expired state.", status=400)
        pending.delete()

        user = UserProfile.objects.filter(id=user_id).first()
        if user is None:
            return HttpResponse("Unknown user.", status=400)

        try:
            token_data = google.exchange_code(code)
        except httpx.HTTPError:
            return HttpResponse("Token exchange failed.", status=502)

        # Lesson 3: refuse to connect if the calendar scope was not actually granted.
        if not google.granted_scopes_ok(token_data.get("scope", "")):
            return HttpResponse(
                "Calendar permission was not granted. Please try again and allow "
                "calendar access.",
                status=400,
            )

        service.save_connection(user, token_data)
        # Bounce back into the app.
        return HttpResponse(
            "<html><body>Google Calendar connected. You can return to LifePilot."
            "<script>window.location='lifepilot://planner';</script></body></html>",
            content_type="text/html",
        )


class CalendarEventsView(APIView):
    def get(self, request):
        day: date = parse_date(request.query_params.get("date", "")) or date.today()
        return Response(service.get_day_events(request.user, day))


class CalendarDisconnectView(APIView):
    def post(self, request):
        GoogleCalendarConnection.objects.filter(user=request.user).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
