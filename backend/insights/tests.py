from datetime import timedelta

from django.utils import timezone
from rest_framework.test import APITestCase

from tasks.models import Task
from users.models import UserProfile
from .models import Habit, HabitLog, UsageEvent


class InsightsTests(APITestCase):
    def setUp(self):
        self.me = UserProfile.objects.create(auth_id="u", email="me@x.co")
        self.patch = __import__("unittest").mock.patch(
            "users.authentication.ClerkJWTAuthentication.authenticate",
            return_value=(self.me, "tok"),
        )

    def test_score_and_counts_derive_from_tasks(self):
        # 3 completed this week, 1 still open → score 75.
        for i in range(3):
            t = Task.objects.create(user=self.me, title=f"done{i}")
            t.mark(True)
            t.save()
        Task.objects.create(user=self.me, title="open")
        with self.patch:
            r = self.client.get("/api/insights/")
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertEqual(data["tasks_completed"], 3)
        self.assertEqual(data["productivity_score"], 75)
        self.assertEqual(len(data["weekly_tasks"]), 7)
        self.assertEqual(len(data["focus_area"]), 7)

    def test_focus_minutes_sum(self):
        now = timezone.now()
        UsageEvent.objects.create(user=self.me, type="focus_session", value=25, occurred_at=now)
        UsageEvent.objects.create(user=self.me, type="focus_session", value=15, occurred_at=now)
        with self.patch:
            r = self.client.get("/api/insights/")
        self.assertEqual(r.json()["focus_minutes"], 40)

    def test_habit_streak(self):
        habit = Habit.objects.create(user=self.me, title="Journal")
        today = timezone.localdate()
        for i in range(4):
            HabitLog.objects.create(habit=habit, date=today - timedelta(days=i), completed=True)
        with self.patch:
            r = self.client.get("/api/insights/")
        self.assertEqual(r.json()["habit_streak"], 4)

    def test_empty_user_scores_100(self):
        with self.patch:
            r = self.client.get("/api/insights/")
        self.assertEqual(r.json()["productivity_score"], 100)
