"""Tests for "Plan my day" (Issue 10.0).

The centre of gravity is the validate-before-write path: propose must never write,
model output must never be trusted, and apply must re-check ownership and slot
freeness against the database.
"""

from datetime import date, time, timedelta
from unittest import mock

from django.utils import timezone
from rest_framework.test import APITestCase

from assistant import ai
from assistant.models import AIUsage
from tasks.models import Task
from users.models import UserProfile

from . import services
from .scheduling import Candidate, build_plan, event_hours, order_candidates

DAY = date(2026, 8, 5)


def as_user(profile):
    return mock.patch(
        "users.authentication.ClerkJWTAuthentication.authenticate",
        return_value=(profile, "tok"),
    )


def no_calendar():
    """gcal degraded/unconnected — the default state without the OAuth credential."""
    return mock.patch(
        "planner.services.get_day_events",
        return_value={"connected": False, "events": [], "all_day": []},
    )


def with_events(events):
    return mock.patch(
        "planner.services.get_day_events",
        return_value={"connected": True, "events": events, "all_day": []},
    )


def event(title, start_hour, end_hour):
    return {
        "id": f"e{start_hour}",
        "title": title,
        "all_day": False,
        "start": f"2026-08-05T{start_hour:02d}:00:00+00:00",
        "end": f"2026-08-05T{end_hour:02d}:00:00+00:00",
    }


# --- Pure scheduling core --------------------------------------------------------


class SchedulingCoreTests(APITestCase):
    def test_event_hours_blocks_span_and_excludes_exact_end(self):
        # 09:00–11:00 occupies 9 and 10, but not 11 (the event is over by then).
        self.assertEqual(event_hours([event("Standup", 9, 11)]), {9, 10})

    def test_event_hours_includes_partial_final_hour(self):
        ev = event("Sync", 9, 10)
        ev["end"] = "2026-08-05T10:30:00+00:00"
        self.assertEqual(event_hours([ev]), {9, 10})

    def test_event_hours_ignores_unparseable(self):
        self.assertEqual(event_hours([{"start": "not-a-date", "end": None}]), set())

    def test_order_is_eisenhower_then_due_date(self):
        overdue_high = Candidate("a", "a", "high", DAY - timedelta(days=1))  # do
        important = Candidate("b", "b", "high", None)  # schedule
        urgent = Candidate("c", "c", "low", DAY)  # delegate
        later = Candidate("d", "d", "low", None)  # later
        ordered = order_candidates([later, urgent, important, overdue_high], DAY)
        self.assertEqual([c.task_id for c in ordered], ["a", "b", "c", "d"])

    def test_build_plan_never_double_books_and_overflows_the_rest(self):
        # Only two free hours (7, 8) — everything else is blocked.
        occupied = set(range(9, 22))
        candidates = [
            Candidate("a", "a", "high", DAY),
            Candidate("b", "b", "high", None),
            Candidate("c", "c", "low", None),
        ]
        plan = build_plan(candidates, occupied, DAY)
        self.assertEqual([(a.task_id, a.hour) for a in plan.assignments], [("a", 7), ("b", 8)])
        self.assertEqual([o.task_id for o in plan.overflow], ["c"])
        self.assertTrue(plan.overflow[0].reason)  # D15: overflow carries a reason

    def test_build_plan_places_nothing_over_an_event(self):
        occupied = event_hours([event("Standup", 7, 9)])
        plan = build_plan([Candidate("a", "a", "high", DAY)], occupied, DAY)
        self.assertEqual(plan.assignments[0].hour, 9)


# --- Model output validation (D11) -----------------------------------------------


class ModelOutputValidationTests(APITestCase):
    def setUp(self):
        self.candidates = [
            Candidate("t1", "one", "high", DAY),
            Candidate("t2", "two", "low", None),
        ]
        self.free = [7, 8, 9]

    def validate(self, data):
        return services.validate_model_plan(data, self.candidates, self.free)

    def test_accepts_a_valid_plan(self):
        plan = self.validate(
            {"assignments": [{"task_id": "t1", "hour": 8}], "overflow": [{"task_id": "t2", "reason": "no room"}]}
        )
        self.assertEqual([(a.task_id, a.hour) for a in plan.assignments], [("t1", 8)])
        self.assertEqual(plan.overflow[0].reason, "no room")

    def test_rejects_task_id_that_is_not_the_users(self):
        """A hallucinated or cross-user id poisons the whole plan."""
        self.assertIsNone(
            self.validate({"assignments": [{"task_id": "someone-elses", "hour": 8}], "overflow": []})
        )

    def test_rejects_hour_outside_the_offered_free_hours(self):
        # 12 is not free — it's an immovable calendar event (D14).
        self.assertIsNone(self.validate({"assignments": [{"task_id": "t1", "hour": 12}], "overflow": []}))

    def test_rejects_double_booking(self):
        self.assertIsNone(
            self.validate(
                {
                    "assignments": [{"task_id": "t1", "hour": 8}, {"task_id": "t2", "hour": 8}],
                    "overflow": [],
                }
            )
        )

    def test_rejects_duplicate_task(self):
        self.assertIsNone(
            self.validate(
                {
                    "assignments": [{"task_id": "t1", "hour": 7}, {"task_id": "t1", "hour": 8}],
                    "overflow": [],
                }
            )
        )

    def test_rejects_malformed_shapes(self):
        for bad in (
            None,
            {},
            {"assignments": "nope", "overflow": []},
            {"assignments": [{"task_id": "t1"}], "overflow": []},
            {"assignments": [{"task_id": "t1", "hour": "8"}], "overflow": []},
            {"assignments": [{"task_id": "t1", "hour": True}], "overflow": []},
            {"assignments": ["t1"], "overflow": []},
        ):
            self.assertIsNone(self.validate(bad), bad)

    def test_forgotten_task_surfaces_as_overflow_never_dropped(self):
        """D15: a task the model omitted entirely must still reach the user."""
        plan = self.validate({"assignments": [{"task_id": "t1", "hour": 7}], "overflow": []})
        self.assertEqual([o.task_id for o in plan.overflow], ["t2"])


# --- Propose / apply API ---------------------------------------------------------


class PlanDayApiTests(APITestCase):
    def setUp(self):
        self.me = UserProfile.objects.create(auth_id="u_me", email="me@x.co")
        self.other = UserProfile.objects.create(auth_id="u_other", email="o@x.co")

    def make_task(self, title, priority="medium", user=None, **kwargs):
        return Task.objects.create(user=user or self.me, title=title, priority=priority, **kwargs)

    def test_propose_writes_nothing(self):
        """D10: the propose call is a preview — the DB is untouched."""
        task = self.make_task("write proposal", priority="high", due_date=DAY)
        with as_user(self.me), no_calendar():
            r = self.client.post("/api/planner/plan-day/", {"date": DAY.isoformat()}, format="json")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(r.json()["assignments"]), 1)

        task.refresh_from_db()
        self.assertIsNone(task.scheduled_date)
        self.assertIsNone(task.scheduled_time)

    def test_propose_plans_around_calendar_events(self):
        """D14: an event at 7–9 pushes the first placement to 9."""
        self.make_task("deep work", priority="high", due_date=DAY)
        with as_user(self.me), with_events([event("Standup", 7, 9)]):
            r = self.client.post("/api/planner/plan-day/", {"date": DAY.isoformat()}, format="json")
        self.assertEqual(r.json()["assignments"][0]["scheduled_time"], "09:00")

    def test_propose_orders_by_priority(self):
        self.make_task("low one", priority="low")
        self.make_task("urgent one", priority="high", due_date=DAY)
        with as_user(self.me), no_calendar():
            assignments = self.client.post(
                "/api/planner/plan-day/", {"date": DAY.isoformat()}, format="json"
            ).json()["assignments"]
        self.assertEqual(assignments[0]["title"], "urgent one")

    def test_propose_logs_token_usage(self):
        """D12: every planning call is accounted for, fallback included."""
        self.make_task("something")
        with as_user(self.me), no_calendar():
            self.client.post("/api/planner/plan-day/", {"date": DAY.isoformat()}, format="json")
        usage = AIUsage.objects.get(user=self.me)
        self.assertEqual(usage.purpose, AIUsage.Purpose.PLAN_DAY)
        self.assertEqual(usage.generated_by, "fallback")

    def test_propose_ignores_other_users_tasks(self):
        self.make_task("not mine", user=self.other)
        with as_user(self.me), no_calendar():
            body = self.client.post(
                "/api/planner/plan-day/", {"date": DAY.isoformat()}, format="json"
            ).json()
        self.assertEqual(body["assignments"], [])

    def test_apply_writes_only_confirmed_placements(self):
        keep = self.make_task("confirmed")
        drop = self.make_task("rejected by user")
        with as_user(self.me), no_calendar():
            r = self.client.post(
                "/api/planner/plan-day/apply/",
                {
                    "date": DAY.isoformat(),
                    "assignments": [{"task_id": str(keep.id), "scheduled_time": "09:00"}],
                },
                format="json",
            )
        self.assertEqual(r.status_code, 200)
        keep.refresh_from_db()
        drop.refresh_from_db()
        self.assertEqual(keep.scheduled_date, DAY)
        self.assertEqual(keep.scheduled_time, time(9, 0))
        self.assertIsNone(drop.scheduled_date)

    def test_apply_rejects_another_users_task(self):
        """Ownership is re-checked at apply time, not trusted from the payload."""
        theirs = self.make_task("not mine", user=self.other)
        with as_user(self.me), no_calendar():
            r = self.client.post(
                "/api/planner/plan-day/apply/",
                {
                    "date": DAY.isoformat(),
                    "assignments": [{"task_id": str(theirs.id), "scheduled_time": "09:00"}],
                },
                format="json",
            )
        self.assertEqual(r.json()["rejected"][0]["reason"], "not_found")
        theirs.refresh_from_db()
        self.assertIsNone(theirs.scheduled_date)

    def test_apply_rejects_a_slot_taken_since_propose(self):
        """State moved between propose and apply — the stale placement is refused."""
        self.make_task("already there", scheduled_date=DAY, scheduled_time=time(9, 0))
        late = self.make_task("too late")
        with as_user(self.me), no_calendar():
            r = self.client.post(
                "/api/planner/plan-day/apply/",
                {
                    "date": DAY.isoformat(),
                    "assignments": [{"task_id": str(late.id), "scheduled_time": "09:00"}],
                },
                format="json",
            )
        self.assertEqual(r.json()["rejected"][0]["reason"], "slot_taken")
        late.refresh_from_db()
        self.assertIsNone(late.scheduled_date)

    def test_apply_refuses_to_double_book_within_one_request(self):
        a = self.make_task("a")
        b = self.make_task("b")
        with as_user(self.me), no_calendar():
            body = self.client.post(
                "/api/planner/plan-day/apply/",
                {
                    "date": DAY.isoformat(),
                    "assignments": [
                        {"task_id": str(a.id), "scheduled_time": "09:00"},
                        {"task_id": str(b.id), "scheduled_time": "09:00"},
                    ],
                },
                format="json",
            )
        self.assertEqual(len(body.json()["applied"]), 1)
        self.assertEqual(body.json()["rejected"][0]["reason"], "slot_taken")

    def test_apply_refuses_a_slot_held_by_a_calendar_event(self):
        """D14 again, at apply time: an event blocks the write even if asked directly."""
        task = self.make_task("over the meeting")
        with as_user(self.me), with_events([event("Standup", 9, 10)]):
            r = self.client.post(
                "/api/planner/plan-day/apply/",
                {
                    "date": DAY.isoformat(),
                    "assignments": [{"task_id": str(task.id), "scheduled_time": "09:00"}],
                },
                format="json",
            )
        self.assertEqual(r.json()["rejected"][0]["reason"], "slot_taken")

    def test_apply_returns_previous_state_for_reversibility(self):
        task = self.make_task("moving", scheduled_date=DAY, scheduled_time=time(8, 0))
        with as_user(self.me), no_calendar():
            body = self.client.post(
                "/api/planner/plan-day/apply/",
                {
                    "date": DAY.isoformat(),
                    "assignments": [{"task_id": str(task.id), "scheduled_time": "11:00"}],
                },
                format="json",
            ).json()
        self.assertEqual(body["previous"][0]["scheduled_time"], "08:00")

    def test_bad_date_is_rejected(self):
        with as_user(self.me), no_calendar():
            r = self.client.post("/api/planner/plan-day/", {"date": "not-a-date"}, format="json")
        self.assertEqual(r.status_code, 400)

    def test_apply_requires_a_list(self):
        with as_user(self.me), no_calendar():
            r = self.client.post(
                "/api/planner/plan-day/apply/", {"assignments": "nope"}, format="json"
            )
        self.assertEqual(r.status_code, 400)

    def test_endpoints_require_authentication(self):
        for path in ("/api/planner/plan-day/", "/api/planner/plan-day/apply/"):
            self.assertEqual(self.client.post(path, {}, format="json").status_code, 401)

    def test_defaults_to_today(self):
        self.make_task("today's work")
        with as_user(self.me), no_calendar():
            body = self.client.post("/api/planner/plan-day/", {}, format="json").json()
        self.assertEqual(body["date"], timezone.localdate().isoformat())


class LiveClaudePathTests(APITestCase):
    """The AI path, exercised with a stubbed model response (no network)."""

    def setUp(self):
        self.me = UserProfile.objects.create(auth_id="u_me", email="me@x.co")

    def test_valid_model_plan_is_used_and_marked_ai(self):
        task = Task.objects.create(user=self.me, title="model placed me")
        stub = ai.StructuredResult(
            data={"assignments": [{"task_id": str(task.id), "hour": 15}], "overflow": []},
            generated_by="ai",
            usage=ai.Usage(model="claude-opus-4-8", input_tokens=120, output_tokens=40),
        )
        with as_user(self.me), no_calendar(), mock.patch(
            "planner.services.ai.propose_schedule", return_value=stub
        ):
            body = self.client.post(
                "/api/planner/plan-day/", {"date": DAY.isoformat()}, format="json"
            ).json()

        self.assertEqual(body["generated_by"], "ai")
        self.assertEqual(body["assignments"][0]["scheduled_time"], "15:00")
        usage = AIUsage.objects.get(user=self.me)
        self.assertEqual((usage.input_tokens, usage.output_tokens), (120, 40))
        # Still a preview: the AI path writes nothing either.
        task.refresh_from_db()
        self.assertIsNone(task.scheduled_date)

    def test_invalid_model_plan_falls_back_to_the_deterministic_plan(self):
        task = Task.objects.create(user=self.me, title="rescued by fallback")
        stub = ai.StructuredResult(
            data={"assignments": [{"task_id": "hallucinated-id", "hour": 15}], "overflow": []},
            generated_by="ai",
            usage=ai.Usage(model="claude-opus-4-8", input_tokens=100, output_tokens=20),
        )
        with as_user(self.me), no_calendar(), mock.patch(
            "planner.services.ai.propose_schedule", return_value=stub
        ):
            body = self.client.post(
                "/api/planner/plan-day/", {"date": DAY.isoformat()}, format="json"
            ).json()

        self.assertEqual(body["generated_by"], "fallback")
        self.assertEqual(body["assignments"][0]["task_id"], str(task.id))
        # The tokens we already spent are still billed to the user (D12).
        self.assertEqual(AIUsage.objects.get(user=self.me).input_tokens, 100)
