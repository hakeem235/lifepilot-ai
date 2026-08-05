"""Tests for the daily review + auto-reschedule (Issue 10.2).

What matters here: the done/slipped split is *accurate* (a review that miscounts
is worse than no review), the roll-forward is a proposal until confirmed, and the
confirm path inherits the auto-scheduler's validation rather than working around it.
"""

from datetime import date, time, timedelta
from unittest import mock

from django.utils import timezone
from rest_framework.test import APITestCase

from assistant.models import AIUsage
from notifications.models import DeviceToken, Notification
from notifications.service import evaluate_and_send, send_daily_reviews
from tasks.models import Task
from users.models import UserProfile

from . import review

DAY = date(2026, 8, 5)
TOMORROW = date(2026, 8, 6)


def as_user(profile):
    return mock.patch(
        "users.authentication.ClerkJWTAuthentication.authenticate",
        return_value=(profile, "tok"),
    )


def no_calendar():
    return mock.patch(
        "planner.review.get_day_events",
        return_value={"connected": False, "events": [], "all_day": []},
    )


def busy_calendar(events):
    return mock.patch(
        "planner.review.get_day_events",
        return_value={"connected": True, "events": events, "all_day": []},
    )


class DoneSlippedSplitTests(APITestCase):
    def setUp(self):
        self.me = UserProfile.objects.create(auth_id="u_me", email="me@x.co")
        self.other = UserProfile.objects.create(auth_id="u_other", email="o@x.co")

    def test_counts_both_scheduled_and_due_tasks(self):
        """The two are different promises; counting one would under-report the day."""
        Task.objects.create(user=self.me, title="on the timeline", scheduled_date=DAY, scheduled_time=time(9, 0))
        Task.objects.create(user=self.me, title="due today", due_date=DAY)
        done, slipped = review.split_day(self.me, DAY)
        self.assertEqual(len(slipped), 2)
        self.assertEqual(done, [])

    def test_a_task_both_scheduled_and_due_is_counted_once(self):
        Task.objects.create(user=self.me, title="both", scheduled_date=DAY, due_date=DAY)
        done, slipped = review.split_day(self.me, DAY)
        self.assertEqual(len(slipped), 1)

    def test_splits_done_from_open(self):
        finished = Task.objects.create(user=self.me, title="finished", due_date=DAY)
        finished.mark(True)
        finished.save()
        Task.objects.create(user=self.me, title="unfinished", due_date=DAY)
        done, slipped = review.split_day(self.me, DAY)
        self.assertEqual([t.title for t in done], ["finished"])
        self.assertEqual([t.title for t in slipped], ["unfinished"])

    def test_ignores_other_days(self):
        Task.objects.create(user=self.me, title="tomorrow's", due_date=TOMORROW)
        done, slipped = review.split_day(self.me, DAY)
        self.assertEqual((done, slipped), ([], []))

    def test_ignores_other_users(self):
        Task.objects.create(user=self.other, title="theirs", due_date=DAY)
        self.assertEqual(review.split_day(self.me, DAY), ([], []))


class ReviewApiTests(APITestCase):
    def setUp(self):
        self.me = UserProfile.objects.create(auth_id="u_me", email="me@x.co")

    def get_review(self, day=DAY):
        with as_user(self.me), no_calendar():
            return self.client.get(f"/api/planner/review/?date={day.isoformat()}")

    def test_reports_an_accurate_done_slipped_split(self):
        finished = Task.objects.create(user=self.me, title="shipped it", due_date=DAY)
        finished.mark(True)
        finished.save()
        Task.objects.create(user=self.me, title="slipped one", due_date=DAY)

        body = self.get_review().json()
        self.assertEqual([d["title"] for d in body["done"]], ["shipped it"])
        self.assertEqual([s["title"] for s in body["slipped"]], ["slipped one"])
        self.assertEqual(body["completion_rate"], 50)

    def test_completion_rate_with_no_tasks_does_not_divide_by_zero(self):
        self.assertEqual(self.get_review().json()["completion_rate"], 0)

    def test_proposes_moves_for_slipped_tasks_into_tomorrow(self):
        Task.objects.create(user=self.me, title="roll me", due_date=DAY, priority="high")
        body = self.get_review().json()
        move = body["proposed_moves"][0]
        self.assertEqual(body["reschedule_date"], TOMORROW.isoformat())
        self.assertEqual(move["scheduled_date"], TOMORROW.isoformat())
        self.assertEqual(move["title"], "roll me")

    def test_review_writes_nothing(self):
        """D10: the review is a preview — the slipped task is untouched."""
        task = Task.objects.create(user=self.me, title="roll me", due_date=DAY)
        self.get_review()
        task.refresh_from_db()
        self.assertIsNone(task.scheduled_date)

    def test_proposed_moves_respect_tomorrows_calendar(self):
        """D14 inherited from the auto-scheduler: an event at 7–9 pushes to 9."""
        Task.objects.create(user=self.me, title="roll me", due_date=DAY)
        with as_user(self.me), busy_calendar(
            [
                {
                    "id": "e1",
                    "title": "Standup",
                    "all_day": False,
                    "start": "2026-08-06T07:00:00+00:00",
                    "end": "2026-08-06T09:00:00+00:00",
                }
            ]
        ):
            body = self.client.get(f"/api/planner/review/?date={DAY.isoformat()}").json()
        self.assertEqual(body["proposed_moves"][0]["scheduled_time"], "09:00")

    def test_proposed_moves_avoid_hours_already_taken_tomorrow(self):
        """D15: tomorrow's 7am is already spoken for, so the move goes to 8."""
        Task.objects.create(
            user=self.me, title="already tomorrow", scheduled_date=TOMORROW, scheduled_time=time(7, 0)
        )
        Task.objects.create(user=self.me, title="roll me", due_date=DAY)
        body = self.get_review().json()
        move = next(m for m in body["proposed_moves"] if m["title"] == "roll me")
        self.assertEqual(move["scheduled_time"], "08:00")

    def test_overflow_is_reported_when_tomorrow_is_full(self):
        for hour in range(7, 22):
            Task.objects.create(
                user=self.me, title=f"busy {hour}", scheduled_date=TOMORROW, scheduled_time=time(hour, 0)
            )
        Task.objects.create(user=self.me, title="no room", due_date=DAY)
        body = self.get_review().json()
        self.assertEqual(body["proposed_moves"], [])
        self.assertEqual(body["overflow"][0]["title"], "no room")
        self.assertTrue(body["overflow"][0]["reason"])

    def test_logs_review_spend(self):
        self.get_review()
        usage = AIUsage.objects.get(user=self.me)
        self.assertEqual(usage.purpose, AIUsage.Purpose.REVIEW)
        self.assertEqual(usage.generated_by, "fallback")

    def test_fallback_summary_is_grounded_in_the_real_counts(self):
        finished = Task.objects.create(user=self.me, title="a", due_date=DAY)
        finished.mark(True)
        finished.save()
        Task.objects.create(user=self.me, title="b", due_date=DAY)
        body = self.get_review().json()
        self.assertIn("1 of 2", body["summary"])

    def test_defaults_to_today(self):
        with as_user(self.me), no_calendar():
            body = self.client.get("/api/planner/review/").json()
        self.assertEqual(body["date"], timezone.localdate().isoformat())

    def test_bad_date_rejected(self):
        with as_user(self.me), no_calendar():
            self.assertEqual(self.client.get("/api/planner/review/?date=nope").status_code, 400)

    def test_requires_authentication(self):
        self.assertEqual(self.client.get("/api/planner/review/").status_code, 401)


class ReviewApplyTests(APITestCase):
    """Apply reuses the auto-scheduler's writer, so it inherits its guarantees."""

    def setUp(self):
        self.me = UserProfile.objects.create(auth_id="u_me", email="me@x.co")
        self.other = UserProfile.objects.create(auth_id="u_other", email="o@x.co")

    def apply(self, moves, target=TOMORROW):
        with as_user(self.me), mock.patch(
            "planner.services.get_day_events",
            return_value={"connected": False, "events": [], "all_day": []},
        ):
            return self.client.post(
                "/api/planner/review/apply/",
                {"reschedule_date": target.isoformat(), "moves": moves},
                format="json",
            )

    def test_only_confirmed_tasks_move(self):
        rolled = Task.objects.create(user=self.me, title="rolled", due_date=DAY)
        left = Task.objects.create(user=self.me, title="left behind", due_date=DAY)
        self.apply([{"task_id": str(rolled.id), "scheduled_time": "09:00"}])
        rolled.refresh_from_db()
        left.refresh_from_db()
        self.assertEqual(rolled.scheduled_date, TOMORROW)
        self.assertEqual(rolled.scheduled_time, time(9, 0))
        self.assertIsNone(left.scheduled_date)

    def test_leaves_the_due_date_alone(self):
        """Rolling the work forward isn't the same as moving the deadline."""
        rolled = Task.objects.create(user=self.me, title="rolled", due_date=DAY)
        self.apply([{"task_id": str(rolled.id), "scheduled_time": "09:00"}])
        rolled.refresh_from_db()
        self.assertEqual(rolled.due_date, DAY)

    def test_rejects_another_users_task(self):
        theirs = Task.objects.create(user=self.other, title="theirs", due_date=DAY)
        body = self.apply([{"task_id": str(theirs.id), "scheduled_time": "09:00"}]).json()
        self.assertEqual(body["rejected"][0]["reason"], "not_found")
        theirs.refresh_from_db()
        self.assertIsNone(theirs.scheduled_date)

    def test_returns_previous_state_so_the_move_is_reversible(self):
        task = Task.objects.create(
            user=self.me, title="was placed", scheduled_date=DAY, scheduled_time=time(15, 0)
        )
        body = self.apply([{"task_id": str(task.id), "scheduled_time": "09:00"}]).json()
        previous = body["previous"][0]
        self.assertEqual(previous["scheduled_date"], DAY.isoformat())
        self.assertEqual(previous["scheduled_time"], "15:00")

    def test_rejects_a_slot_taken_since_the_review_was_shown(self):
        Task.objects.create(
            user=self.me, title="got there first", scheduled_date=TOMORROW, scheduled_time=time(9, 0)
        )
        late = Task.objects.create(user=self.me, title="late", due_date=DAY)
        body = self.apply([{"task_id": str(late.id), "scheduled_time": "09:00"}]).json()
        self.assertEqual(body["rejected"][0]["reason"], "slot_taken")

    def test_moves_must_be_a_list(self):
        with as_user(self.me):
            r = self.client.post("/api/planner/review/apply/", {"moves": "nope"}, format="json")
        self.assertEqual(r.status_code, 400)

    def test_bad_reschedule_date_rejected(self):
        with as_user(self.me):
            r = self.client.post(
                "/api/planner/review/apply/", {"reschedule_date": "nope", "moves": []}, format="json"
            )
        self.assertEqual(r.status_code, 400)

    def test_defaults_to_tomorrow(self):
        task = Task.objects.create(user=self.me, title="rolled", due_date=DAY)
        with as_user(self.me), mock.patch(
            "planner.services.get_day_events",
            return_value={"connected": False, "events": [], "all_day": []},
        ):
            self.client.post(
                "/api/planner/review/apply/",
                {"moves": [{"task_id": str(task.id), "scheduled_time": "09:00"}]},
                format="json",
            )
        task.refresh_from_db()
        self.assertEqual(task.scheduled_date, timezone.localdate() + timedelta(days=1))

    def test_requires_authentication(self):
        self.assertEqual(self.client.post("/api/planner/review/apply/", {}).status_code, 401)


class ReviewNudgeTests(APITestCase):
    """The evening trigger rides the existing 9.4 scheduled job."""

    def setUp(self):
        self.me = UserProfile.objects.create(
            auth_id="u_me", email="me@x.co", timezone="America/Los_Angeles"
        )
        DeviceToken.objects.create(user=self.me, token="ExponentPushToken[x]", platform="ios")

    def at_utc(self, hour):
        return timezone.now().replace(hour=hour, minute=0, second=0, microsecond=0)

    def test_fires_at_the_users_local_review_hour(self):
        # 20:00 in Los Angeles is 03:00 UTC the next day.
        with mock.patch("notifications.service.push.send_push"):
            created = send_daily_reviews(self.at_utc(3))
        self.assertEqual(len(created), 1)
        self.assertEqual(created[0].kind, Notification.Kind.DAILY_REVIEW)

    def test_does_not_fire_at_the_wrong_local_hour(self):
        with mock.patch("notifications.service.push.send_push"):
            self.assertEqual(send_daily_reviews(self.at_utc(12)), [])

    def test_fires_only_once_per_day(self):
        """A job running every five minutes must not nudge twelve times an hour."""
        with mock.patch("notifications.service.push.send_push"):
            first = send_daily_reviews(self.at_utc(3))
            second = send_daily_reviews(self.at_utc(3))
        self.assertEqual((len(first), len(second)), (1, 0))

    def test_skips_users_with_no_device(self):
        DeviceToken.objects.all().delete()
        with mock.patch("notifications.service.push.send_push"):
            self.assertEqual(send_daily_reviews(self.at_utc(3)), [])

    def test_unknown_timezone_falls_back_to_utc(self):
        self.me.timezone = "Mars/Olympus_Mons"
        self.me.save()
        with mock.patch("notifications.service.push.send_push"):
            self.assertEqual(len(send_daily_reviews(self.at_utc(20))), 1)

    def test_the_scheduled_job_includes_the_review_nudge(self):
        with mock.patch("notifications.service.push.send_push"):
            created = evaluate_and_send(self.at_utc(3))
        self.assertTrue(any(n.kind == Notification.Kind.DAILY_REVIEW for n in created))

    def test_the_nudge_spends_no_ai_tokens(self):
        """D12: the cron nudges; the summary is generated only if the user opens it."""
        with mock.patch("notifications.service.push.send_push"):
            send_daily_reviews(self.at_utc(3))
        self.assertEqual(AIUsage.objects.count(), 0)
