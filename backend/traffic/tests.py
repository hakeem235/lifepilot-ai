"""Traffic tests. No network: mapbox.geocode/drive are patched throughout."""

from __future__ import annotations

from datetime import timedelta
from unittest.mock import patch

from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from users.models import UserProfile

from . import service
from .settings_store import get_origin, set_origin


def make_user(auth_id="user-1", email="a@example.com"):
    return UserProfile.objects.create(auth_id=auth_id, email=email, timezone="UTC")


def event(title="Client review", location="Kingdom Centre, Riyadh", minutes_ahead=120, all_day=False):
    start = timezone.now() + timedelta(minutes=minutes_ahead)
    return {
        "id": "e1",
        "title": title,
        "all_day": all_day,
        "start": start.isoformat(),
        "end": (start + timedelta(hours=1)).isoformat(),
        "location": location,
    }


class ClassifyTests(TestCase):
    def test_levels_by_congestion_ratio(self):
        self.assertEqual(service.classify(600, 600), "light")
        self.assertEqual(service.classify(720, 600), "moderate")  # 1.2x
        self.assertEqual(service.classify(900, 600), "heavy")  # 1.5x

    def test_unknown_without_a_free_flow_baseline(self):
        # Guessing "light" here could label gridlock as clear. Say nothing instead.
        self.assertEqual(service.classify(600, None), "unknown")
        self.assertEqual(service.classify(600, 0), "unknown")


class NextEventSelectionTests(TestCase):
    def test_picks_the_earliest_upcoming_located_event(self):
        now = timezone.now()
        chosen = service.next_event_with_location(
            [event(title="Later", minutes_ahead=300), event(title="Sooner", minutes_ahead=60)], now
        )
        self.assertEqual(chosen["title"], "Sooner")

    def test_skips_events_without_a_venue(self):
        now = timezone.now()
        self.assertIsNone(service.next_event_with_location([event(location="")], now))
        self.assertIsNone(service.next_event_with_location([event(location="   ")], now))

    def test_skips_all_day_and_past_events(self):
        now = timezone.now()
        self.assertIsNone(service.next_event_with_location([event(all_day=True)], now))
        self.assertIsNone(service.next_event_with_location([event(minutes_ahead=-30)], now))

    def test_tolerates_an_unparseable_start(self):
        bad = event()
        bad["start"] = "not-a-date"
        self.assertIsNone(service.next_event_with_location([bad], timezone.now()))


CONNECTED_DAY = {"connected": True, "events": [], "all_day": []}


@override_settings(MAPBOX_ACCESS_TOKEN="test-token")
class NextCommuteTests(TestCase):
    def setUp(self):
        self.user = make_user()
        set_origin(self.user, "Home, Riyadh")

    def _day(self, events):
        return {"connected": True, "events": events, "all_day": []}

    def test_happy_path_returns_leave_by_before_the_event(self):
        ev = event(minutes_ahead=120)
        with (
            patch("traffic.service.get_day_events", return_value=self._day([ev])),
            patch("traffic.mapbox.geocode", side_effect=[(46.6, 24.7), (46.7, 24.8)]),
            patch(
                "traffic.mapbox.drive",
                return_value={"duration": 1200.0, "duration_typical": 900.0, "distance": 8400.0},
            ),
        ):
            result = service.next_commute(self.user, get_origin(self.user))

        self.assertTrue(result["available"])
        self.assertEqual(result["duration_minutes"], 20)
        self.assertEqual(result["level"], "moderate")
        self.assertEqual(result["distance_km"], 8.4)
        self.assertEqual(result["event_title"], "Client review")
        # leave_by must be exactly the drive time before the event starts.
        self.assertLess(result["leave_by"], result["event_start"])

    def test_unconfigured_token_degrades_rather_than_raising(self):
        with override_settings(MAPBOX_ACCESS_TOKEN=""):
            result = service.next_commute(self.user, "Home")
        self.assertEqual(result, {"available": False, "reason": "not_configured"})

    def test_missing_origin_is_reported_not_guessed(self):
        result = service.next_commute(self.user, "  ")
        self.assertEqual(result["reason"], "no_origin")

    def test_calendar_not_connected(self):
        with patch("traffic.service.get_day_events", return_value={"connected": False}):
            result = service.next_commute(self.user, "Home")
        self.assertEqual(result["reason"], "calendar_not_connected")

    def test_no_located_event(self):
        with patch("traffic.service.get_day_events", return_value=CONNECTED_DAY):
            result = service.next_commute(self.user, "Home")
        self.assertEqual(result["reason"], "no_upcoming_event_with_location")

    def test_unresolvable_venue_reports_destination_not_found(self):
        # "Zoom" as a location is normal, not an error.
        with (
            patch("traffic.service.get_day_events", return_value=self._day([event(location="Zoom")])),
            patch("traffic.mapbox.geocode", side_effect=[(46.6, 24.7), None]),
        ):
            result = service.next_commute(self.user, "Home")
        self.assertEqual(result["reason"], "destination_not_found")

    def test_mapbox_outage_degrades_to_lookup_failed(self):
        with (
            patch("traffic.service.get_day_events", return_value=self._day([event()])),
            patch("traffic.mapbox.geocode", side_effect=RuntimeError("boom")),
        ):
            result = service.next_commute(self.user, "Home")
        self.assertEqual(result["reason"], "lookup_failed")

    def test_no_drivable_route(self):
        with (
            patch("traffic.service.get_day_events", return_value=self._day([event()])),
            patch("traffic.mapbox.geocode", side_effect=[(46.6, 24.7), (46.7, 24.8)]),
            patch("traffic.mapbox.drive", return_value=None),
        ):
            result = service.next_commute(self.user, "Home")
        self.assertEqual(result["reason"], "no_route")

    def test_missing_typical_duration_still_returns_an_estimate(self):
        with (
            patch("traffic.service.get_day_events", return_value=self._day([event()])),
            patch("traffic.mapbox.geocode", side_effect=[(46.6, 24.7), (46.7, 24.8)]),
            patch(
                "traffic.mapbox.drive",
                return_value={"duration": 600.0, "duration_typical": None, "distance": 5000.0},
            ),
        ):
            result = service.next_commute(self.user, "Home")
        self.assertTrue(result["available"])
        self.assertEqual(result["level"], "unknown")


class OriginStoreTests(TestCase):
    def setUp(self):
        self.user = make_user()

    def test_round_trip_and_trimming(self):
        self.assertEqual(get_origin(self.user), "")
        set_origin(self.user, "  King Fahd Rd, Riyadh  ")
        self.assertEqual(get_origin(self.user), "King Fahd Rd, Riyadh")

    def test_does_not_clobber_other_personalization_keys(self):
        from users.models import UserSettings

        obj, _ = UserSettings.objects.get_or_create(user=self.user)
        obj.personalization = {"greeting": "Hi"}
        obj.save()

        set_origin(self.user, "Somewhere")
        obj.refresh_from_db()
        self.assertEqual(obj.personalization["greeting"], "Hi")
        self.assertEqual(obj.personalization["commute_origin"], "Somewhere")


class EndpointAuthTests(TestCase):
    def test_next_commute_requires_authentication(self):
        res = APIClient().get(reverse("next-commute"))
        self.assertIn(res.status_code, (401, 403))

    def test_origin_requires_authentication(self):
        res = APIClient().put(reverse("commute-origin"), {"origin": "x"}, format="json")
        self.assertIn(res.status_code, (401, 403))
