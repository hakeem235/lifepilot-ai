"""Tests for the Templates API: preset visibility, apply-to-day, user scoping."""

from unittest import mock

from rest_framework.test import APITestCase

from tasks.models import Task
from users.models import UserProfile

from .models import TaskTemplate, TemplateItem


def as_user(profile):
    return mock.patch(
        "users.authentication.ClerkJWTAuthentication.authenticate",
        return_value=(profile, "tok"),
    )


class TemplateApiTests(APITestCase):
    def setUp(self):
        self.me = UserProfile.objects.create(auth_id="u_me", email="me@x.co")
        self.other = UserProfile.objects.create(auth_id="u_other", email="o@x.co")

    def test_presets_seeded_and_listed(self):
        with as_user(self.me):
            r = self.client.get("/api/templates/")
            names = {t["name"] for t in r.json()}
        self.assertEqual(r.status_code, 200)
        self.assertIn("Morning Routine", names)
        self.assertIn("Deep Work", names)
        # Presets carry ordered items and are flagged as presets.
        morning = next(t for t in r.json() if t["name"] == "Morning Routine")
        self.assertTrue(morning["is_preset"])
        self.assertGreaterEqual(len(morning["items"]), 3)

    def test_apply_creates_tasks_on_day(self):
        tpl = TaskTemplate.objects.create(user=None, name="T")
        TemplateItem.objects.create(template=tpl, title="A", priority="high", order=0, time_offset_minutes=7 * 60)
        TemplateItem.objects.create(template=tpl, title="B", priority="low", order=1, time_offset_minutes=8 * 60 + 30)
        with as_user(self.me):
            r = self.client.post(f"/api/templates/{tpl.id}/apply/", {"date": "2026-08-10"}, format="json")
        self.assertEqual(r.status_code, 201)
        created = r.json()["created"]
        self.assertEqual(len(created), 2)
        self.assertEqual({c["title"] for c in created}, {"A", "B"})
        a = next(c for c in created if c["title"] == "A")
        self.assertEqual(a["scheduled_date"], "2026-08-10")
        self.assertEqual(a["scheduled_time"], "07:00:00")
        self.assertEqual(a["priority"], "high")
        b = next(c for c in created if c["title"] == "B")
        self.assertEqual(b["scheduled_time"], "08:30:00")
        # Tasks are owned by the applying user.
        self.assertEqual(Task.objects.filter(user=self.me).count(), 2)

    def test_apply_requires_date(self):
        tpl = TaskTemplate.objects.create(user=None, name="T")
        with as_user(self.me):
            r = self.client.post(f"/api/templates/{tpl.id}/apply/", {}, format="json")
        self.assertEqual(r.status_code, 400)

    def test_cannot_see_or_apply_others_private_template(self):
        tpl = TaskTemplate.objects.create(user=self.other, name="Private")
        with as_user(self.me):
            listing = self.client.get("/api/templates/").json()
            self.assertNotIn("Private", {t["name"] for t in listing})
            r = self.client.post(f"/api/templates/{tpl.id}/apply/", {"date": "2026-08-10"}, format="json")
            self.assertEqual(r.status_code, 404)

    def test_own_template_visible(self):
        TaskTemplate.objects.create(user=self.me, name="Mine")
        with as_user(self.me):
            names = {t["name"] for t in self.client.get("/api/templates/").json()}
        self.assertIn("Mine", names)
