"""Tests for the Google Calendar overlay (Issue 9.3).

Network is always mocked — no test hits Google. Focus areas: graceful
degradation with no creds, the scope-drop guard (Base44 lesson 3), event
mapping (timed vs all-day), and per-user isolation.
"""

from unittest import mock

from django.core import signing
from django.test import override_settings
from rest_framework.test import APITestCase

from users.models import UserProfile

from . import google
from .models import ConnectionClaim, GoogleCalendarConnection, PendingOAuth
from .views import STATE_SALT


def initiate_state(user):
    """Mimic auth-url: record a single-use nonce and return the signed state."""
    nonce = "test-nonce-" + str(user.id)
    PendingOAuth.objects.create(user=user, nonce=nonce)
    return signing.dumps({"u": str(user.id), "n": nonce}, salt=STATE_SALT)

CONFIGURED = dict(
    GOOGLE_OAUTH_CLIENT_ID="cid",
    GOOGLE_OAUTH_CLIENT_SECRET="secret",
    GOOGLE_OAUTH_REDIRECT_URI="http://localhost:8000/api/gcal/callback/",
)


def as_user(profile):
    return mock.patch(
        "users.authentication.ClerkJWTAuthentication.authenticate",
        return_value=(profile, "tok"),
    )


class PureHelperTests(APITestCase):
    def test_granted_scopes_ok(self):
        self.assertTrue(google.granted_scopes_ok(f"openid {google.CALENDAR_SCOPE}"))
        self.assertFalse(google.granted_scopes_ok("openid email"))
        self.assertFalse(google.granted_scopes_ok(""))

    def test_map_event_timed_vs_all_day(self):
        timed = google.map_event(
            {"id": "1", "summary": "Standup",
             "start": {"dateTime": "2026-08-05T09:00:00Z"},
             "end": {"dateTime": "2026-08-05T09:30:00Z"}}
        )
        self.assertFalse(timed["all_day"])
        self.assertEqual(timed["title"], "Standup")

        allday = google.map_event(
            {"id": "2", "summary": "Holiday",
             "start": {"date": "2026-08-05"}, "end": {"date": "2026-08-06"}}
        )
        self.assertTrue(allday["all_day"])

    def test_map_event_carries_location_for_the_commute_estimate(self):
        located = google.map_event(
            {"id": "3", "summary": "Client review", "location": "  Kingdom Centre, Riyadh  ",
             "start": {"dateTime": "2026-08-05T13:00:00Z"},
             "end": {"dateTime": "2026-08-05T14:00:00Z"}}
        )
        self.assertEqual(located["location"], "Kingdom Centre, Riyadh")

        # Most events have no venue; that must be an empty string, not None,
        # so the traffic selector can skip it with a plain falsiness check.
        bare = google.map_event(
            {"id": "4", "summary": "Focus", "start": {"dateTime": "2026-08-05T15:00:00Z"},
             "end": {"dateTime": "2026-08-05T16:00:00Z"}}
        )
        self.assertEqual(bare["location"], "")

    @override_settings(**CONFIGURED)
    def test_build_auth_url_requests_readonly_scope_and_pkce(self):
        url = google.build_auth_url("state123", "challenge123")
        self.assertIn("calendar.readonly", url)
        self.assertIn("access_type=offline", url)
        self.assertIn("state=state123", url)
        self.assertIn("code_challenge=challenge123", url)
        self.assertIn("code_challenge_method=S256", url)

    def test_pkce_pair_is_s256(self):
        import base64
        import hashlib

        verifier, challenge = google.pkce_pair()
        expected = (
            base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest())
            .rstrip(b"=")
            .decode()
        )
        self.assertEqual(challenge, expected)
        self.assertNotEqual(verifier, challenge)


class EndpointTests(APITestCase):
    def setUp(self):
        self.me = UserProfile.objects.create(auth_id="u_me", email="me@x.co")
        self.other = UserProfile.objects.create(auth_id="u_other", email="o@x.co")

    def test_status_and_events_degrade_without_config(self):
        with as_user(self.me):
            s = self.client.get("/api/gcal/status/").json()
            self.assertFalse(s["configured"])
            self.assertFalse(s["connected"])
            e = self.client.get("/api/gcal/events/?date=2026-08-05").json()
            self.assertEqual(e, {"connected": False, "events": [], "all_day": []})

    def test_auth_url_503_when_unconfigured(self):
        with as_user(self.me):
            r = self.client.get("/api/gcal/auth-url/")
            self.assertEqual(r.status_code, 503)

    @override_settings(**CONFIGURED)
    def test_auth_url_returns_consent_url(self):
        with as_user(self.me):
            r = self.client.get("/api/gcal/auth-url/")
            self.assertEqual(r.status_code, 200)
            self.assertIn("calendar.readonly", r.json()["url"])

    @override_settings(**CONFIGURED)
    def test_callback_rejects_bad_state(self):
        r = self.client.get("/api/gcal/callback/?code=abc&state=tampered")
        self.assertEqual(r.status_code, 400)

    @override_settings(**CONFIGURED)
    def test_callback_refuses_when_scope_dropped(self):
        """Lesson 3: if calendar scope isn't granted, do not mark connected."""
        state = initiate_state(self.me)
        with mock.patch.object(
            google, "exchange_code",
            return_value={"access_token": "a", "scope": "openid email", "expires_in": 3600},
        ):
            r = self.client.get(f"/api/gcal/callback/?code=abc&state={state}")
        self.assertEqual(r.status_code, 400)
        self.assertFalse(GoogleCalendarConnection.objects.filter(user=self.me).exists())

    @override_settings(**CONFIGURED)
    def test_callback_stows_claim_without_binding(self):
        """Valid callback creates a claim + redirect, but binds NOTHING to a user."""
        state = initiate_state(self.me)
        with mock.patch.object(
            google, "exchange_code",
            return_value={
                "access_token": "a", "refresh_token": "r",
                "scope": google.CALENDAR_SCOPE, "expires_in": 3600,
            },
        ):
            r = self.client.get(f"/api/gcal/callback/?code=abc&state={state}")
        self.assertEqual(r.status_code, 200)
        self.assertIn("gcal_claim=", r.content.decode())
        self.assertEqual(ConnectionClaim.objects.count(), 1)
        # Crucially: no connection is bound until an authenticated finalize.
        self.assertFalse(GoogleCalendarConnection.objects.filter(user=self.me).exists())

    @override_settings(**CONFIGURED)
    def test_finalize_binds_to_authenticated_user(self):
        """The claim binds tokens to whoever finalizes (authenticated), not to state."""
        cc = ConnectionClaim.objects.create(
            claim="claim123",
            token_data={
                "access_token": "a", "refresh_token": "r",
                "scope": google.CALENDAR_SCOPE, "expires_in": 3600,
            },
        )
        with as_user(self.me):
            r = self.client.post("/api/gcal/finalize/", {"claim": "claim123"}, format="json")
        self.assertEqual(r.status_code, 204)
        self.assertTrue(GoogleCalendarConnection.objects.filter(user=self.me).exists())
        self.assertFalse(ConnectionClaim.objects.filter(pk=cc.pk).exists())  # single-use

    @override_settings(**CONFIGURED)
    def test_finalize_rejects_unknown_claim(self):
        with as_user(self.me):
            r = self.client.post("/api/gcal/finalize/", {"claim": "nope"}, format="json")
        self.assertEqual(r.status_code, 400)
        self.assertFalse(GoogleCalendarConnection.objects.filter(user=self.me).exists())

    @override_settings(**CONFIGURED)
    def test_finalize_claim_is_single_use(self):
        ConnectionClaim.objects.create(
            claim="claim123",
            token_data={"access_token": "a", "scope": google.CALENDAR_SCOPE, "expires_in": 3600},
        )
        with as_user(self.me):
            first = self.client.post("/api/gcal/finalize/", {"claim": "claim123"}, format="json")
            second = self.client.post("/api/gcal/finalize/", {"claim": "claim123"}, format="json")
        self.assertEqual(first.status_code, 204)
        self.assertEqual(second.status_code, 400)

    @override_settings(**CONFIGURED)
    def test_callback_rejects_unknown_nonce(self):
        """A validly-signed state with no matching initiation record is refused."""
        state = signing.dumps({"u": str(self.me.id), "n": "never-issued"}, salt=STATE_SALT)
        with mock.patch.object(google, "exchange_code") as exch:
            r = self.client.get(f"/api/gcal/callback/?code=abc&state={state}")
        self.assertEqual(r.status_code, 400)
        exch.assert_not_called()  # rejected before any token exchange

    @override_settings(**CONFIGURED)
    def test_callback_nonce_is_single_use(self):
        """Replaying a consumed state fails (nonce deleted on first use)."""
        state = initiate_state(self.me)
        good = {
            "access_token": "a", "refresh_token": "r",
            "scope": google.CALENDAR_SCOPE, "expires_in": 3600,
        }
        with mock.patch.object(google, "exchange_code", return_value=good):
            first = self.client.get(f"/api/gcal/callback/?code=abc&state={state}")
            second = self.client.get(f"/api/gcal/callback/?code=abc&state={state}")
        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 400)

    @override_settings(**CONFIGURED)
    def test_events_maps_when_connected(self):
        GoogleCalendarConnection.objects.create(
            user=self.me, access_token="a", refresh_token="r", scope=google.CALENDAR_SCOPE,
        )
        raw = [
            {"id": "1", "summary": "Standup",
             "start": {"dateTime": "2026-08-05T09:00:00Z"}, "end": {"dateTime": "2026-08-05T09:30:00Z"}},
            {"id": "2", "summary": "Holiday",
             "start": {"date": "2026-08-05"}, "end": {"date": "2026-08-06"}},
        ]
        with mock.patch.object(google, "fetch_events_raw", return_value=raw), \
                mock.patch("gcal.service.GoogleCalendarConnection.is_expired", return_value=False):
            with as_user(self.me):
                e = self.client.get("/api/gcal/events/?date=2026-08-05").json()
        self.assertTrue(e["connected"])
        self.assertEqual(len(e["events"]), 1)
        self.assertEqual(len(e["all_day"]), 1)
        self.assertEqual(e["events"][0]["title"], "Standup")

    @override_settings(**CONFIGURED)
    def test_connection_is_per_user(self):
        GoogleCalendarConnection.objects.create(user=self.other, access_token="a")
        with as_user(self.me):
            s = self.client.get("/api/gcal/status/").json()
        self.assertFalse(s["connected"])  # me has no connection; other's is invisible
