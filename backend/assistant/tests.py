"""Tests for the AI endpoints — focus on the fallback path (no key set), which is
the app's default runtime state, plus history persistence and grounding."""

from unittest import mock

from rest_framework.test import APITestCase

from tasks.models import Task
from users.models import UserProfile
from . import ai
from .models import CopilotMessage, DailySummary


def as_user(profile):
    return mock.patch(
        "users.authentication.ClerkJWTAuthentication.authenticate",
        return_value=(profile, "tok"),
    )


class AiServiceFallbackTests(APITestCase):
    def test_brief_fallback_grounds_in_counts(self):
        r = ai.daily_brief({"open_tasks": 3, "due_today": 2, "high_priority": 1})
        self.assertEqual(r.generated_by, "fallback")
        self.assertIn("3 open task", r.text)

    def test_brief_fallback_all_clear(self):
        r = ai.daily_brief({"open_tasks": 0})
        self.assertIn("all clear", r.text.lower())

    def test_chat_fallback_plan_lists_tasks(self):
        r = ai.chat("plan my day", {"open_tasks": 2, "task_titles": ["A", "B"]})
        self.assertEqual(r.generated_by, "fallback")
        self.assertIn("A", r.text)


class AiEndpointTests(APITestCase):
    def setUp(self):
        self.me = UserProfile.objects.create(auth_id="u", email="me@x.co")
        Task.objects.create(user=self.me, title="Ship 8.2", priority="high")

    def test_brief_endpoint_persists_summary(self):
        with as_user(self.me):
            r = self.client.get("/api/ai/brief/")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["open_tasks"], 1)
        self.assertTrue(DailySummary.objects.filter(user=self.me).exists())

    def test_chat_endpoint_persists_history(self):
        with as_user(self.me):
            r = self.client.post("/api/ai/chat/", {"message": "plan my day"}, format="json")
            self.assertEqual(r.status_code, 200)
            self.assertIn("reply", r.json())
            hist = self.client.get("/api/ai/chat/").json()
        self.assertEqual(len(hist), 2)  # user + assistant
        self.assertEqual(CopilotMessage.objects.filter(user=self.me).count(), 2)

    def test_chat_requires_message(self):
        with as_user(self.me):
            r = self.client.post("/api/ai/chat/", {"message": "  "}, format="json")
        self.assertEqual(r.status_code, 400)

    def test_real_ai_path_used_when_complete_returns_text(self):
        # When Claude returns text, generated_by flips to "ai".
        with mock.patch("assistant.ai._complete", return_value="Real Claude answer."):
            r = ai.chat("hi", {"open_tasks": 0, "task_titles": []})
        self.assertEqual(r.generated_by, "ai")
        self.assertEqual(r.text, "Real Claude answer.")
