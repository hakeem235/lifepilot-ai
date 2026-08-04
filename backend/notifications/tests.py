"""Tests for notifications (Issue 9.4): the scheduled job's evaluation logic,
idempotency, push delivery, and the user-scoped in-app center."""

from datetime import timedelta
from unittest import mock

from django.utils import timezone
from rest_framework.test import APITestCase

from tasks.models import Task
from users.models import UserProfile

from .models import DeviceToken, Notification
from .service import evaluate_and_send


def as_user(profile):
    return mock.patch(
        "users.authentication.ClerkJWTAuthentication.authenticate",
        return_value=(profile, "tok"),
    )


class ScheduledJobTests(APITestCase):
    def setUp(self):
        self.me = UserProfile.objects.create(auth_id="u_me", email="me@x.co")
        DeviceToken.objects.create(user=self.me, token="ExponentPushToken[abc]")
        self.now = timezone.now()

    def _task_starting_in(self, minutes):
        dt = self.now + timedelta(minutes=minutes)
        local = timezone.localtime(dt)
        return Task.objects.create(
            user=self.me, title="Standup", status="open",
            scheduled_date=local.date(), scheduled_time=local.time().replace(microsecond=0),
        )

    @mock.patch("notifications.service.push.send_push")
    def test_task_start_fires_within_window_and_pushes(self, send_push):
        self._task_starting_in(3)
        created = evaluate_and_send(now=self.now)
        self.assertEqual(len(created), 1)
        self.assertEqual(created[0].kind, "task_start")
        send_push.assert_called_once()
        self.assertEqual(send_push.call_args.args[0], ["ExponentPushToken[abc]"])

    @mock.patch("notifications.service.push.send_push")
    def test_task_start_not_fired_outside_window(self, send_push):
        self._task_starting_in(30)  # too far out
        created = evaluate_and_send(now=self.now)
        self.assertEqual(created, [])
        send_push.assert_not_called()

    @mock.patch("notifications.service.push.send_push")
    def test_job_is_idempotent(self, send_push):
        self._task_starting_in(2)
        first = evaluate_and_send(now=self.now)
        second = evaluate_and_send(now=self.now)
        self.assertEqual(len(first), 1)
        self.assertEqual(second, [])  # dedupe_key prevents a second alert
        self.assertEqual(Notification.objects.count(), 1)

    @mock.patch("notifications.service.push.send_push")
    def test_deadline_fires_for_high_priority_due_soon(self, send_push):
        Task.objects.create(
            user=self.me, title="Report", status="open", priority="high",
            due_date=self.now.date(),
        )
        created = evaluate_and_send(now=self.now)
        self.assertEqual(len(created), 1)
        self.assertEqual(created[0].kind, "deadline")

    @mock.patch("notifications.service.push.send_push")
    def test_deadline_ignores_low_priority(self, send_push):
        Task.objects.create(
            user=self.me, title="Chore", status="open", priority="low",
            due_date=self.now.date(),
        )
        self.assertEqual(evaluate_and_send(now=self.now), [])


class NotificationApiTests(APITestCase):
    def setUp(self):
        self.me = UserProfile.objects.create(auth_id="u_me", email="me@x.co")
        self.other = UserProfile.objects.create(auth_id="u_other", email="o@x.co")

    def _notif(self, user, key):
        return Notification.objects.create(
            user=user, kind="task_start", title="t", body="b", dedupe_key=key
        )

    def test_register_device(self):
        with as_user(self.me):
            r = self.client.post(
                "/api/notifications/register/", {"token": "ExponentPushToken[x]"}, format="json"
            )
            self.assertEqual(r.status_code, 204)
        self.assertTrue(DeviceToken.objects.filter(user=self.me).exists())

    def test_list_returns_unread_count_scoped_to_user(self):
        self._notif(self.me, "k1")
        self._notif(self.other, "k2")  # another user's — must not appear
        with as_user(self.me):
            data = self.client.get("/api/notifications/").json()
        self.assertEqual(len(data["notifications"]), 1)
        self.assertEqual(data["unread"], 1)

    def test_mark_read_and_read_all(self):
        n1 = self._notif(self.me, "k1")
        self._notif(self.me, "k2")
        with as_user(self.me):
            self.client.post(f"/api/notifications/{n1.id}/read/")
            after_one = self.client.get("/api/notifications/").json()
            self.assertEqual(after_one["unread"], 1)
            self.client.post("/api/notifications/read-all/")
            after_all = self.client.get("/api/notifications/").json()
            self.assertEqual(after_all["unread"], 0)

    def test_cannot_read_others_notification(self):
        n = self._notif(self.other, "k1")
        with as_user(self.me):
            r = self.client.post(f"/api/notifications/{n.id}/read/")
            self.assertEqual(r.status_code, 404)
