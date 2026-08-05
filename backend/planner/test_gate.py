"""The proposal → apply gate audit (Issue 10.3, D10).

This file is the enforcing test for the phase's central safety property:

    No AI-originated write happens without a distinct, user-confirmed apply step.

It is written to hold for endpoints that **don't exist yet**. Rather than
re-testing each of 10.0–10.2 by hand, it walks the planner URLconf and holds
every registered endpoint to its own declaration — so an AI feature added in a
later phase that quietly writes from a proposal path fails CI. Passing it by
mislabelling an endpoint requires editing a `writes = ...` line, which is a
reviewable act rather than an oversight.
"""

from datetime import date, time
from unittest import mock

from django.urls import get_resolver
from rest_framework.test import APITestCase

from assistant.models import AIUsage
from tasks.models import Task
from users.models import UserProfile

from .gate import ApplyEndpoint, PlannerEndpoint, ProposalEndpoint

DAY = date(2026, 8, 5)


def as_user(profile):
    return mock.patch(
        "users.authentication.ClerkJWTAuthentication.authenticate",
        return_value=(profile, "tok"),
    )


class no_calendar:
    """Neutralise the calendar in every module that imported it by name.

    `from gcal.service import get_day_events` binds the function into each
    module, so patching the source module alone would miss them — and a patch
    that silently misses is exactly how an audit like this rots.
    """

    TARGETS = ("planner.services.get_day_events", "planner.review.get_day_events")
    EMPTY = {"connected": False, "events": [], "all_day": []}

    def __enter__(self):
        self._patches = [mock.patch(t, return_value=self.EMPTY) for t in self.TARGETS]
        for patch in self._patches:
            patch.start()
        return self

    def __exit__(self, *exc):
        for patch in self._patches:
            patch.stop()
        return False


def planner_endpoints():
    """Every view registered under /api/planner/, with its URL pattern."""
    found = []
    for pattern in get_resolver().url_patterns:
        for sub in getattr(pattern, "url_patterns", []):
            cls = getattr(sub.callback, "cls", None)
            route = str(pattern.pattern) + str(sub.pattern)
            if cls is not None and route.startswith("api/planner/"):
                found.append((route, cls))
    return found


class GateRegistrationTests(APITestCase):
    """Every planner endpoint must declare which side of the gate it is on."""

    def test_endpoints_were_discovered(self):
        """Guard against the audit silently passing because it found nothing."""
        self.assertGreaterEqual(len(planner_endpoints()), 7)

    def test_every_endpoint_inherits_the_gate(self):
        for route, cls in planner_endpoints():
            self.assertTrue(
                issubclass(cls, PlannerEndpoint),
                f"{route} ({cls.__name__}) bypasses the propose/apply gate",
            )

    def test_every_endpoint_declares_whether_it_writes(self):
        for route, cls in planner_endpoints():
            self.assertIn(
                cls.writes, (True, False), f"{route} ({cls.__name__}) does not declare `writes`"
            )

    def test_declaration_matches_the_base_class(self):
        for route, cls in planner_endpoints():
            if issubclass(cls, ApplyEndpoint):
                self.assertTrue(cls.writes, route)
            elif issubclass(cls, ProposalEndpoint):
                self.assertFalse(cls.writes, route)

    def test_apply_endpoints_are_reached_by_post_only(self):
        """A write must never be reachable by a GET, which clients retry freely."""
        for route, cls in planner_endpoints():
            if cls.writes:
                self.assertFalse(hasattr(cls, "get"), f"{route} exposes a GET that writes")

    def test_every_endpoint_requires_authentication(self):
        for route, cls in planner_endpoints():
            path = "/" + route
            status = self.client.post(path, {}, format="json").status_code
            self.assertEqual(status, 401, f"{route} is reachable unauthenticated")


class ProposalWritesNothingTests(APITestCase):
    """The core D10 assertion, applied to every proposal endpoint generically."""

    def setUp(self):
        self.me = UserProfile.objects.create(auth_id="u_me", email="me@x.co")
        # A realistic starting state: a tray task, a placed task, and a done one.
        self.tray = Task.objects.create(user=self.me, title="in the tray", priority="high", due_date=DAY)
        self.placed = Task.objects.create(
            user=self.me, title="placed", scheduled_date=DAY, scheduled_time=time(9, 0)
        )
        done = Task.objects.create(user=self.me, title="finished", due_date=DAY)
        done.mark(True)
        done.save()

    def snapshot(self):
        """Every field of every task that any AI path could plausibly touch."""
        return sorted(
            Task.objects.values_list(
                "id", "title", "notes", "due_date", "scheduled_date", "scheduled_time",
                "priority", "status", "progress", "source", "completed_at",
            )
        )

    def test_no_proposal_endpoint_changes_any_task(self):
        bodies = {
            "api/planner/plan-day/": {"date": DAY.isoformat()},
            "api/planner/capture/": {"message": "call the dentist tomorrow at 2pm"},
            "api/planner/review/": {"date": DAY.isoformat()},
        }
        before = self.snapshot()
        count_before = Task.objects.count()

        for route, cls in planner_endpoints():
            if cls.writes:
                continue
            path = "/" + route
            with as_user(self.me), no_calendar():
                # Exercise whichever verb the endpoint actually exposes.
                if hasattr(cls, "post"):
                    self.client.post(path, bodies.get(route, {}), format="json")
                if hasattr(cls, "get"):
                    self.client.get(path, bodies.get(route, {}))

            self.assertEqual(
                self.snapshot(), before, f"{route} mutated a task while only proposing"
            )
            self.assertEqual(
                Task.objects.count(), count_before, f"{route} created or deleted a task"
            )

    def test_proposals_do_log_ai_spend(self):
        """Spend logging is not a user-data write — it must still happen (D12)."""
        with as_user(self.me), no_calendar():
            self.client.post("/api/planner/plan-day/", {"date": DAY.isoformat()}, format="json")
        self.assertEqual(AIUsage.objects.count(), 1)


class ApplyRevalidatesTests(APITestCase):
    """Apply endpoints must re-check ownership from the DB, not trust the payload."""

    def setUp(self):
        self.me = UserProfile.objects.create(auth_id="u_me", email="me@x.co")
        self.other = UserProfile.objects.create(auth_id="u_other", email="o@x.co")
        self.theirs = Task.objects.create(user=self.other, title="not mine", due_date=DAY)

    def test_no_apply_endpoint_touches_another_users_task(self):
        payloads = {
            "api/planner/plan-day/apply/": {
                "date": DAY.isoformat(),
                "assignments": [{"task_id": str(self.theirs.id), "scheduled_time": "09:00"}],
            },
            "api/planner/review/apply/": {
                "reschedule_date": DAY.isoformat(),
                "moves": [{"task_id": str(self.theirs.id), "scheduled_time": "09:00"}],
            },
            "api/planner/undo/": {
                "previous": [
                    {
                        "task_id": str(self.theirs.id),
                        "scheduled_date": DAY.isoformat(),
                        "scheduled_time": "09:00",
                    }
                ],
                "created_task_ids": [str(self.theirs.id)],
            },
        }
        for route, payload in payloads.items():
            with as_user(self.me), no_calendar():
                self.client.post("/" + route, payload, format="json")
            self.theirs.refresh_from_db()
            self.assertIsNone(self.theirs.scheduled_date, f"{route} moved another user's task")
        self.assertTrue(Task.objects.filter(id=self.theirs.id).exists())


class UndoTests(APITestCase):
    """Reversibility: an applied change can be walked back (10.3 acceptance)."""

    def setUp(self):
        self.me = UserProfile.objects.create(auth_id="u_me", email="me@x.co")
        self.other = UserProfile.objects.create(auth_id="u_other", email="o@x.co")

    def undo(self, previous=None, created=None):
        with as_user(self.me):
            return self.client.post(
                "/api/planner/undo/",
                {"previous": previous or [], "created_task_ids": created or []},
                format="json",
            )

    def test_an_applied_plan_can_be_fully_undone(self):
        """The end-to-end acceptance case: plan → apply → undo → back to the tray."""
        task = Task.objects.create(user=self.me, title="plan me", priority="high", due_date=DAY)
        with as_user(self.me), no_calendar():
            proposal = self.client.post(
                "/api/planner/plan-day/", {"date": DAY.isoformat()}, format="json"
            ).json()
            applied = self.client.post(
                "/api/planner/plan-day/apply/",
                {"date": DAY.isoformat(), "assignments": proposal["assignments"]},
                format="json",
            ).json()

        task.refresh_from_db()
        self.assertIsNotNone(task.scheduled_date)

        self.undo(previous=applied["previous"])
        task.refresh_from_db()
        self.assertIsNone(task.scheduled_date)
        self.assertIsNone(task.scheduled_time)

    def test_undo_restores_a_previous_slot_rather_than_clearing_it(self):
        task = Task.objects.create(
            user=self.me, title="moved", scheduled_date=DAY, scheduled_time=time(15, 0)
        )
        task.scheduled_time = time(9, 0)
        task.save()
        self.undo(
            previous=[
                {"task_id": str(task.id), "scheduled_date": DAY.isoformat(), "scheduled_time": "15:00"}
            ]
        )
        task.refresh_from_db()
        self.assertEqual(task.scheduled_time, time(15, 0))

    def test_undo_deletes_a_task_the_ai_created(self):
        task = Task.objects.create(user=self.me, title="captured", source=Task.Source.AI)
        body = self.undo(created=[str(task.id)]).json()
        self.assertEqual(body["deleted"], [str(task.id)])
        self.assertFalse(Task.objects.filter(id=task.id).exists())

    def test_undo_refuses_to_delete_a_task_the_user_made(self):
        """Deletion is unrecoverable — it is limited to what the AI brought into being."""
        task = Task.objects.create(user=self.me, title="mine", source=Task.Source.MANUAL)
        body = self.undo(created=[str(task.id)]).json()
        self.assertEqual(body["rejected"][0]["reason"], "not_ai_created")
        self.assertTrue(Task.objects.filter(id=task.id).exists())

    def test_undo_will_not_delete_another_users_ai_task(self):
        theirs = Task.objects.create(user=self.other, title="theirs", source=Task.Source.AI)
        body = self.undo(created=[str(theirs.id)]).json()
        self.assertEqual(body["rejected"][0]["reason"], "not_found")
        self.assertTrue(Task.objects.filter(id=theirs.id).exists())

    def test_undo_tolerates_malformed_entries(self):
        body = self.undo(previous=["nope", {"task_id": "not-a-uuid"}, {}]).json()
        self.assertEqual(body["restored"], [])
        self.assertEqual(len(body["rejected"]), 3)

    def test_undo_is_idempotent_for_a_deleted_task(self):
        task = Task.objects.create(user=self.me, title="captured", source=Task.Source.AI)
        self.undo(created=[str(task.id)])
        body = self.undo(created=[str(task.id)]).json()
        self.assertEqual(body["deleted"], [])
        self.assertEqual(body["rejected"][0]["reason"], "not_found")

    def test_a_captured_task_can_be_undone_end_to_end(self):
        with as_user(self.me):
            created = self.client.post(
                "/api/planner/capture/apply/",
                {"draft": {"title": "Call the dentist", "priority": "medium"}},
                format="json",
            ).json()
        task_id = created["task"]["id"]
        self.assertTrue(Task.objects.filter(id=task_id).exists())

        self.undo(created=[task_id])
        self.assertFalse(Task.objects.filter(id=task_id).exists())
