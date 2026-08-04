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
from .models import GoogleCalendarConnection
from .views import STATE_SALT

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

    @override_settings(**CONFIGURED)
    def test_build_auth_url_requests_readonly_scope(self):
        url = google.build_auth_url("state123")
        self.assertIn("calendar.readonly", url)
        self.assertIn("access_type=offline", url)
        self.assertIn("state=state123", url)


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
        state = signing.dumps(str(self.me.id), salt=STATE_SALT)
        with mock.patch.object(
            google, "exchange_code",
            return_value={"access_token": "a", "scope": "openid email", "expires_in": 3600},
        ):
            r = self.client.get(f"/api/gcal/callback/?code=abc&state={state}")
        self.assertEqual(r.status_code, 400)
        self.assertFalse(GoogleCalendarConnection.objects.filter(user=self.me).exists())

    @override_settings(**CONFIGURED)
    def test_callback_connects_on_valid_scope(self):
        state = signing.dumps(str(self.me.id), salt=STATE_SALT)
        with mock.patch.object(
            google, "exchange_code",
            return_value={
                "access_token": "a", "refresh_token": "r",
                "scope": google.CALENDAR_SCOPE, "expires_in": 3600,
            },
        ):
            r = self.client.get(f"/api/gcal/callback/?code=abc&state={state}")
        self.assertEqual(r.status_code, 200)
        self.assertTrue(GoogleCalendarConnection.objects.filter(user=self.me).exists())

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
