"""Tests for the Tasks API: user scoping, segments, and check-to-complete."""

from datetime import timedelta
from unittest import mock

from django.utils import timezone
from rest_framework.test import APITestCase

from users.models import UserProfile
from .models import Task


def as_user(profile):
    """Force-authenticate by patching the Clerk auth to return the given profile."""
    return mock.patch(
        "users.authentication.ClerkJWTAuthentication.authenticate",
        return_value=(profile, "tok"),
    )


class TaskApiTests(APITestCase):
    def setUp(self):
        self.me = UserProfile.objects.create(auth_id="u_me", email="me@x.co")
        self.other = UserProfile.objects.create(auth_id="u_other", email="o@x.co")

    def test_create_and_list_scoped_to_user(self):
        with as_user(self.me):
            r = self.client.post("/api/tasks/", {"title": "Buy milk"}, format="json")
            self.assertEqual(r.status_code, 201)
            r = self.client.get("/api/tasks/")
            self.assertEqual(len(r.json()), 1)

    def test_user_cannot_see_others_tasks(self):
        Task.objects.create(user=self.other, title="secret")
        with as_user(self.me):
            r = self.client.get("/api/tasks/")
            self.assertEqual(r.json(), [])

    def test_user_cannot_mutate_others_task(self):
        t = Task.objects.create(user=self.other, title="secret")
        with as_user(self.me):
            r = self.client.post(f"/api/tasks/{t.id}/complete/", {}, format="json")
            self.assertEqual(r.status_code, 404)

    def test_segments(self):
        today = timezone.localdate()
        Task.objects.create(user=self.me, title="today", due_date=today)
        Task.objects.create(user=self.me, title="soon", due_date=today + timedelta(days=3))
        done = Task.objects.create(user=self.me, title="done", due_date=today)
        done.mark(True)
        done.save()
        with as_user(self.me):
            self.assertEqual(len(self.client.get("/api/tasks/?segment=today").json()), 1)
            self.assertEqual(len(self.client.get("/api/tasks/?segment=upcoming").json()), 1)
            self.assertEqual(len(self.client.get("/api/tasks/?segment=completed").json()), 1)

    def test_schedule_task_onto_timeline(self):
        """Dragging a tray task onto a slot PATCHes scheduled_date + time."""
        t = Task.objects.create(user=self.me, title="plan me")
        with as_user(self.me):
            r = self.client.patch(
                f"/api/tasks/{t.id}/",
                {"scheduled_date": "2026-08-05", "scheduled_time": "09:00"},
                format="json",
            )
            self.assertEqual(r.status_code, 200)
            self.assertEqual(r.json()["scheduled_date"], "2026-08-05")
            self.assertEqual(r.json()["scheduled_time"], "09:00:00")
        t.refresh_from_db()
        self.assertEqual(str(t.scheduled_date), "2026-08-05")

    def test_reschedule_changes_slot(self):
        """Dragging slot→slot updates the time in place."""
        t = Task.objects.create(
            user=self.me, title="move me", scheduled_date="2026-08-05", scheduled_time="09:00"
        )
        with as_user(self.me):
            r = self.client.patch(
                f"/api/tasks/{t.id}/", {"scheduled_time": "14:00"}, format="json"
            )
            self.assertEqual(r.json()["scheduled_time"], "14:00:00")

    def test_unschedule_returns_task_to_tray(self):
        """Dragging a slot task back to the tray clears its schedule."""
        t = Task.objects.create(
            user=self.me, title="unplan", scheduled_date="2026-08-05", scheduled_time="09:00"
        )
        with as_user(self.me):
            r = self.client.patch(
                f"/api/tasks/{t.id}/",
                {"scheduled_date": None, "scheduled_time": None},
                format="json",
            )
            self.assertIsNone(r.json()["scheduled_date"])
        t.refresh_from_db()
        self.assertIsNone(t.scheduled_date)

    def test_planner_filters(self):
        """?scheduled_date returns that day; ?unscheduled=true returns the tray."""
        Task.objects.create(
            user=self.me, title="on day", scheduled_date="2026-08-05", scheduled_time="09:00"
        )
        Task.objects.create(
            user=self.me, title="other day", scheduled_date="2026-08-06"
        )
        Task.objects.create(user=self.me, title="in tray")
        with as_user(self.me):
            day = self.client.get("/api/tasks/?scheduled_date=2026-08-05").json()
            self.assertEqual([t["title"] for t in day], ["on day"])
            tray = self.client.get("/api/tasks/?unscheduled=true").json()
            self.assertEqual([t["title"] for t in tray], ["in tray"])

    def test_cannot_schedule_others_task(self):
        t = Task.objects.create(user=self.other, title="secret")
        with as_user(self.me):
            r = self.client.patch(
                f"/api/tasks/{t.id}/", {"scheduled_date": "2026-08-05"}, format="json"
            )
            self.assertEqual(r.status_code, 404)

    def test_complete_toggles_and_persists(self):
        t = Task.objects.create(user=self.me, title="x")
        with as_user(self.me):
            r = self.client.post(f"/api/tasks/{t.id}/complete/", {"done": True}, format="json")
            self.assertEqual(r.status_code, 200)
            self.assertEqual(r.json()["status"], "done")
            self.assertEqual(r.json()["progress"], 100)
        t.refresh_from_db()
        self.assertIsNotNone(t.completed_at)
        with as_user(self.me):
            r = self.client.post(f"/api/tasks/{t.id}/complete/", {"done": False}, format="json")
            self.assertEqual(r.json()["status"], "open")
        t.refresh_from_db()
        self.assertIsNone(t.completed_at)
