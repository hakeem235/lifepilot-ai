"""Google Calendar endpoints (Issue 9.3, hardened).

- status / auth-url / events / disconnect / finalize are Clerk-authenticated.
- callback is public (Google's browser redirect hits it). It verifies the signed
  single-use state, PKCE-exchanges the code, checks the granted scope includes
  calendar.readonly (Base44 lesson 3), and — crucially — does NOT bind tokens to
  a user. It stows them under a random claim delivered only to the device that
  completed consent; the app then calls the authenticated /finalize to bind them
  to the real Clerk identity (account-linking-CSRF defense).
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

from . import google, service
from .models import ConnectionClaim, GoogleCalendarConnection, PendingOAuth

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
        # initiation by this user (replay + CSRF defense). PKCE verifier ties the
        # code exchange to this initiation.
        nonce = secrets.token_urlsafe(32)
        verifier, challenge = google.pkce_pair()
        PendingOAuth.objects.create(user=request.user, nonce=nonce, code_verifier=verifier)
        state = signing.dumps({"u": str(request.user.id), "n": nonce}, salt=STATE_SALT)
        return Response({"url": google.build_auth_url(state, challenge)})


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
        verifier = pending.code_verifier
        pending.delete()

        try:
            token_data = google.exchange_code(code, verifier)
        except httpx.HTTPError:
            return HttpResponse("Token exchange failed.", status=502)

        # Lesson 3: refuse to connect if the calendar scope was not actually granted.
        if not google.granted_scopes_ok(token_data.get("scope", "")):
            return HttpResponse(
                "Calendar permission was not granted. Please try again and allow "
                "calendar access.",
                status=400,
            )

        # Do NOT bind tokens to a user here. Stow them under a random claim and hand
        # it back only to the device that completed consent; the app finalizes with
        # its authenticated identity, so tokens can't be bound to an attacker's
        # pre-baked state (account-linking-CSRF defense).
        claim = secrets.token_urlsafe(32)
        ConnectionClaim.objects.create(claim=claim, token_data=token_data)
        return HttpResponse(
            "<html><body>Google Calendar connected. You can return to LifePilot."
            f"<script>window.location='lifepilot://planner?gcal_claim={claim}';</script>"
            "</body></html>",
            content_type="text/html",
        )


class CalendarFinalizeView(APIView):
    def post(self, request):
        claim = (request.data.get("claim") or "").strip()
        pending = ConnectionClaim.objects.filter(claim=claim).first() if claim else None
        if pending is None or not pending.is_fresh(STATE_MAX_AGE):
            if pending is not None:
                pending.delete()
            return Response(
                {"detail": "Invalid or expired claim."}, status=status.HTTP_400_BAD_REQUEST
            )
        service.save_connection(request.user, pending.token_data)
        pending.delete()  # single-use
        return Response(status=status.HTTP_204_NO_CONTENT)


class CalendarEventsView(APIView):
    def get(self, request):
        day: date = parse_date(request.query_params.get("date", "")) or date.today()
        return Response(service.get_day_events(request.user, day))


class CalendarDisconnectView(APIView):
    def post(self, request):
        GoogleCalendarConnection.objects.filter(user=request.user).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
