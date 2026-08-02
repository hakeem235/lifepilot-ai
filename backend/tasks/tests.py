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
