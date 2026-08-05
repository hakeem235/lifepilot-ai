"""Tests for natural-language capture (Issue 10.1).

Two things are being proven:

1. **Date resolution is the server's job and it is correct** — including across a
   day boundary, where a user's "tomorrow" and UTC's "tomorrow" disagree.
2. **Model output is never trusted** — malformed drafts are repaired to safe
   defaults or rejected outright, and nothing is written without an apply call.

The model itself isn't under test (no live key); each representative phrase is
represented by the structured draft Claude would return for it, which is exactly
the surface the server is responsible for.
"""

from datetime import date, datetime, time
from unittest import mock
from zoneinfo import ZoneInfo

from rest_framework.test import APITestCase

from assistant import ai
from assistant.models import AIUsage
from tasks.models import Task
from users.models import UserProfile

from . import capture
from .dates import resolve_date, resolve_time, user_today

# A Wednesday, so weekday resolution has somewhere to go in both directions.
TODAY = date(2026, 8, 5)


def as_user(profile):
    return mock.patch(
        "users.authentication.ClerkJWTAuthentication.authenticate",
        return_value=(profile, "tok"),
    )


def model_returns(data):
    """Stub the Haiku capture call with the draft it would produce."""
    return mock.patch(
        "planner.capture.ai.parse_capture",
        return_value=ai.StructuredResult(
            data=data,
            generated_by="ai",
            usage=ai.Usage(model="claude-haiku-4-5-20251001", input_tokens=60, output_tokens=25),
        ),
    )


def model_unavailable():
    return mock.patch(
        "planner.capture.ai.parse_capture",
        return_value=ai.StructuredResult(data=None, generated_by="fallback"),
    )


# --- Date resolution -------------------------------------------------------------


class DateResolutionTests(APITestCase):
    def test_relative_days(self):
        self.assertEqual(
            resolve_date({"date_mode": "relative", "relative_days": 1}, TODAY), date(2026, 8, 6)
        )
        self.assertEqual(
            resolve_date({"date_mode": "relative", "relative_days": 0}, TODAY), TODAY
        )

    def test_none_mode_yields_no_date(self):
        self.assertIsNone(resolve_date({"date_mode": "none"}, TODAY))

    def test_weekday_resolves_forward(self):
        # Wednesday → Friday is two days out.
        self.assertEqual(
            resolve_date({"date_mode": "weekday", "weekday": "friday"}, TODAY), date(2026, 8, 7)
        )

    def test_same_weekday_means_a_week_out(self):
        """'Wednesday' said on a Wednesday means the next one, not today."""
        self.assertEqual(
            resolve_date({"date_mode": "weekday", "weekday": "wednesday"}, TODAY),
            date(2026, 8, 12),
        )

    def test_next_weekday_adds_a_week(self):
        self.assertEqual(
            resolve_date(
                {"date_mode": "weekday", "weekday": "friday", "weekday_which": "next"}, TODAY
            ),
            date(2026, 8, 14),
        )

    def test_absolute_date(self):
        self.assertEqual(
            resolve_date({"date_mode": "absolute", "absolute_date": "2026-09-01"}, TODAY),
            date(2026, 9, 1),
        )

    def test_rejects_invalid_specs(self):
        for spec in (
            {"date_mode": "bogus"},
            {"date_mode": "relative", "relative_days": "tomorrow"},
            {"date_mode": "relative", "relative_days": True},
            {"date_mode": "relative", "relative_days": -3},
            {"date_mode": "relative", "relative_days": 9999},
            {"date_mode": "weekday", "weekday": "someday"},
            {"date_mode": "absolute", "absolute_date": "not-a-date"},
            {"date_mode": "absolute", "absolute_date": "2031-01-01"},  # hallucinated far future
            {},
        ):
            self.assertIsNone(resolve_date(spec, TODAY), spec)

    def test_time_resolution(self):
        self.assertEqual(resolve_time({"hour": 14, "minute": 30}), time(14, 30))
        self.assertEqual(resolve_time({"hour": 9}), time(9, 0))

    def test_rejects_invalid_times(self):
        for spec in ({"hour": 25}, {"hour": "2pm"}, {"hour": True}, {"minute": 30}, {}):
            self.assertIsNone(resolve_time(spec), spec)

    def test_bad_minute_degrades_to_the_hour(self):
        self.assertEqual(resolve_time({"hour": 9, "minute": "half past"}), time(9, 0))


class DayBoundaryTests(APITestCase):
    """'Tomorrow' must mean the user's tomorrow, not the server's."""

    def test_user_ahead_of_utc_is_already_on_the_next_day(self):
        # 23:30 UTC on the 5th is 11:30 on the 6th in Auckland (UTC+12).
        moment = datetime(2026, 8, 5, 23, 30, tzinfo=ZoneInfo("UTC"))
        self.assertEqual(user_today("Pacific/Auckland", moment), date(2026, 8, 6))
        self.assertEqual(user_today("UTC", moment), date(2026, 8, 5))

    def test_user_behind_utc_is_still_on_the_previous_day(self):
        # 02:00 UTC on the 6th is 19:00 on the 5th in Los Angeles (UTC-7).
        moment = datetime(2026, 8, 6, 2, 0, tzinfo=ZoneInfo("UTC"))
        self.assertEqual(user_today("America/Los_Angeles", moment), date(2026, 8, 5))

    def test_tomorrow_differs_by_timezone_at_the_boundary(self):
        moment = datetime(2026, 8, 5, 23, 30, tzinfo=ZoneInfo("UTC"))
        spec = {"date_mode": "relative", "relative_days": 1}
        self.assertEqual(resolve_date(spec, user_today("Pacific/Auckland", moment)), date(2026, 8, 7))
        self.assertEqual(resolve_date(spec, user_today("UTC", moment)), date(2026, 8, 6))

    def test_unknown_timezone_falls_back_to_utc(self):
        moment = datetime(2026, 8, 5, 23, 30, tzinfo=ZoneInfo("UTC"))
        self.assertEqual(user_today("Mars/Olympus_Mons", moment), date(2026, 8, 5))


# --- Draft building from representative phrases ----------------------------------


class DraftBuildingTests(APITestCase):
    """Each case is the draft Claude returns for the phrase in its docstring."""

    def build(self, data, message="…"):
        return capture.build_draft(data, TODAY, message)

    def test_relative_date_with_time(self):
        """'remind me to call the dentist tomorrow 2pm'"""
        draft = self.build(
            {
                "title": "Call the dentist",
                "date_mode": "relative",
                "relative_days": 1,
                "hour": 14,
                "minute": 0,
                "priority": "medium",
            }
        )
        self.assertEqual(draft["title"], "Call the dentist")
        self.assertEqual(draft["due_date"], "2026-08-06")
        self.assertEqual(draft["scheduled_date"], "2026-08-06")
        self.assertEqual(draft["scheduled_time"], "14:00")

    def test_bare_title(self):
        """'buy milk'"""
        draft = self.build({"title": "Buy milk", "date_mode": "none", "priority": "medium"})
        self.assertEqual(draft["title"], "Buy milk")
        self.assertIsNone(draft["due_date"])
        self.assertIsNone(draft["scheduled_date"])

    def test_priority_word(self):
        """'urgent: send the invoice today'"""
        draft = self.build(
            {
                "title": "Send the invoice",
                "date_mode": "relative",
                "relative_days": 0,
                "priority": "high",
            }
        )
        self.assertEqual(draft["priority"], "high")
        self.assertEqual(draft["due_date"], TODAY.isoformat())

    def test_date_without_a_time_stays_in_the_tray(self):
        """'call mom on friday' — dated, but with no slot to render in."""
        draft = self.build(
            {"title": "Call mom", "date_mode": "weekday", "weekday": "friday", "priority": "medium"}
        )
        self.assertEqual(draft["due_date"], "2026-08-07")
        self.assertIsNone(draft["scheduled_date"])
        self.assertIsNone(draft["scheduled_time"])

    def test_time_without_a_date_is_dropped(self):
        """A time with nothing to anchor it to can't schedule anything."""
        draft = self.build(
            {"title": "Standup", "date_mode": "none", "hour": 9, "priority": "medium"}
        )
        self.assertIsNone(draft["scheduled_time"])

    def test_invalid_priority_falls_back_to_medium(self):
        draft = self.build({"title": "Thing", "date_mode": "none", "priority": "URGENT!!"})
        self.assertEqual(draft["priority"], "medium")

    def test_rejects_a_draft_with_no_usable_title(self):
        for data in (None, {}, {"title": "   ", "date_mode": "none", "priority": "low"}, "nope"):
            self.assertIsNone(self.build(data), data)

    def test_strips_nul_and_control_characters(self):
        """Postgres rejects NUL outright; DRF chokes on control chars ([PHASE-6])."""
        draft = self.build(
            {"title": "Call\x00 the\x07 dentist", "date_mode": "none", "priority": "medium"}
        )
        self.assertEqual(draft["title"], "Call the dentist")

    def test_truncates_an_overlong_title(self):
        draft = self.build({"title": "x" * 500, "date_mode": "none", "priority": "medium"})
        self.assertEqual(len(draft["title"]), 255)


class FallbackDraftTests(APITestCase):
    def test_keeps_the_title_and_drops_the_date(self):
        """No model means no date — guessing one is worse than leaving it out."""
        draft = capture.fallback_draft("call the dentist tomorrow 2pm")
        self.assertEqual(draft["title"], "call the dentist tomorrow 2pm")
        self.assertIsNone(draft["due_date"])
        self.assertIsNone(draft["scheduled_time"])

    def test_empty_message_yields_nothing(self):
        self.assertIsNone(capture.fallback_draft("   "))


# --- API -------------------------------------------------------------------------


class CaptureApiTests(APITestCase):
    def setUp(self):
        self.me = UserProfile.objects.create(auth_id="u_me", email="me@x.co", timezone="UTC")
        self.other = UserProfile.objects.create(auth_id="u_other", email="o@x.co")

    def test_capture_creates_no_task(self):
        """D10: capture is a preview — the task exists only after apply."""
        draft = {
            "title": "Call the dentist",
            "date_mode": "relative",
            "relative_days": 1,
            "hour": 14,
            "priority": "medium",
        }
        with as_user(self.me), model_returns(draft):
            r = self.client.post(
                "/api/planner/capture/",
                {"message": "remind me to call the dentist tomorrow 2pm"},
                format="json",
            )
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["draft"]["title"], "Call the dentist")
        self.assertEqual(Task.objects.count(), 0)

    def test_capture_logs_usage_against_the_cheap_model(self):
        """D12/D13: capture spend is tracked and runs on Haiku."""
        with as_user(self.me), model_returns(
            {"title": "Thing", "date_mode": "none", "priority": "medium"}
        ):
            self.client.post("/api/planner/capture/", {"message": "thing"}, format="json")
        usage = AIUsage.objects.get(user=self.me)
        self.assertEqual(usage.purpose, AIUsage.Purpose.CAPTURE)
        self.assertEqual(usage.model, "claude-haiku-4-5-20251001")

    def test_capture_falls_back_when_the_model_is_unavailable(self):
        with as_user(self.me), model_unavailable():
            body = self.client.post(
                "/api/planner/capture/", {"message": "buy milk"}, format="json"
            ).json()
        self.assertEqual(body["generated_by"], "fallback")
        self.assertEqual(body["draft"]["title"], "buy milk")
        self.assertIsNone(body["draft"]["due_date"])

    def test_malformed_model_output_falls_back_rather_than_writing_garbage(self):
        with as_user(self.me), model_returns({"title": "", "date_mode": "relative"}):
            body = self.client.post(
                "/api/planner/capture/", {"message": "something"}, format="json"
            ).json()
        self.assertEqual(body["generated_by"], "fallback")
        self.assertEqual(body["draft"]["title"], "something")
        self.assertEqual(Task.objects.count(), 0)

    def test_capture_flags_an_occupied_slot(self):
        Task.objects.create(
            user=self.me, title="already here", scheduled_date=date(2026, 8, 6), scheduled_time=time(14, 0)
        )
        draft = {
            "title": "Call the dentist",
            "date_mode": "absolute",
            "absolute_date": "2026-08-06",
            "hour": 14,
            "priority": "medium",
        }
        with as_user(self.me), model_returns(draft), mock.patch(
            "planner.capture.user_today", return_value=date(2026, 8, 5)
        ):
            body = self.client.post(
                "/api/planner/capture/", {"message": "dentist"}, format="json"
            ).json()
        self.assertTrue(body["slot_conflict"])

    def test_empty_message_rejected(self):
        with as_user(self.me):
            r = self.client.post("/api/planner/capture/", {"message": "   "}, format="json")
        self.assertEqual(r.status_code, 400)

    def test_overlong_message_rejected(self):
        with as_user(self.me):
            r = self.client.post("/api/planner/capture/", {"message": "x" * 1001}, format="json")
        self.assertEqual(r.status_code, 400)

    def test_apply_creates_the_confirmed_task(self):
        with as_user(self.me):
            r = self.client.post(
                "/api/planner/capture/apply/",
                {
                    "draft": {
                        "title": "Call the dentist",
                        "notes": "",
                        "priority": "high",
                        "due_date": "2026-08-06",
                        "scheduled_date": "2026-08-06",
                        "scheduled_time": "14:00",
                    }
                },
                format="json",
            )
        self.assertEqual(r.status_code, 201)
        task = Task.objects.get()
        self.assertEqual(task.user, self.me)
        self.assertEqual(task.title, "Call the dentist")
        self.assertEqual(task.scheduled_time, time(14, 0))
        self.assertEqual(task.source, Task.Source.AI)

    def test_apply_respects_the_users_edits(self):
        """The draft came back through the client — its edited values are what land."""
        with as_user(self.me):
            self.client.post(
                "/api/planner/capture/apply/",
                {
                    "draft": {
                        "title": "Call the orthodontist",
                        "priority": "low",
                        "due_date": "2026-08-09",
                        "scheduled_date": None,
                        "scheduled_time": None,
                    }
                },
                format="json",
            )
        task = Task.objects.get()
        self.assertEqual(task.title, "Call the orthodontist")
        self.assertEqual(task.priority, "low")
        self.assertIsNone(task.scheduled_date)

    def test_apply_will_not_double_book_but_keeps_the_task(self):
        """D15: the placement is dropped, the task is not."""
        Task.objects.create(
            user=self.me, title="already here", scheduled_date=date(2026, 8, 6), scheduled_time=time(14, 0)
        )
        with as_user(self.me):
            body = self.client.post(
                "/api/planner/capture/apply/",
                {
                    "draft": {
                        "title": "Call the dentist",
                        "priority": "medium",
                        "due_date": "2026-08-06",
                        "scheduled_date": "2026-08-06",
                        "scheduled_time": "14:00",
                    }
                },
                format="json",
            ).json()
        self.assertEqual(body["warning"], "slot_taken")
        created = Task.objects.get(title="Call the dentist")
        self.assertIsNone(created.scheduled_date)
        self.assertEqual(created.due_date, date(2026, 8, 6))

    def test_apply_rejects_a_titleless_draft(self):
        with as_user(self.me):
            for draft in (None, {}, {"title": "  "}, "nope"):
                r = self.client.post(
                    "/api/planner/capture/apply/", {"draft": draft}, format="json"
                )
                self.assertEqual(r.status_code, 400, draft)
        self.assertEqual(Task.objects.count(), 0)

    def test_apply_ignores_malformed_dates_rather_than_erroring(self):
        with as_user(self.me):
            r = self.client.post(
                "/api/planner/capture/apply/",
                {
                    "draft": {
                        "title": "Thing",
                        "priority": "medium",
                        "due_date": "not-a-date",
                        "scheduled_time": "99:99",
                    }
                },
                format="json",
            )
        self.assertEqual(r.status_code, 201)
        task = Task.objects.get()
        self.assertIsNone(task.due_date)
        self.assertIsNone(task.scheduled_time)

    def test_apply_scopes_the_task_to_the_caller(self):
        """A draft can't smuggle in another user — ownership comes from the session."""
        with as_user(self.me):
            self.client.post(
                "/api/planner/capture/apply/",
                {"draft": {"title": "Mine", "priority": "medium", "user": str(self.other.id)}},
                format="json",
            )
        self.assertEqual(Task.objects.get().user, self.me)

    def test_endpoints_require_authentication(self):
        for path in ("/api/planner/capture/", "/api/planner/capture/apply/"):
            self.assertEqual(self.client.post(path, {}, format="json").status_code, 401)
