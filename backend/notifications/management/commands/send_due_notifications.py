"""Scheduled job (Issue 9.4, D8): evaluate tasks and deliver due notifications.

Run on a schedule (cron / Render cron job), e.g. every 5 minutes:
    python manage.py send_due_notifications
This is the backend delivery path — it fires whether or not the app is open.
"""

from django.core.management.base import BaseCommand

from notifications.service import evaluate_and_send


class Command(BaseCommand):
    help = "Evaluate tasks and send due task-start / deadline notifications."

    def handle(self, *args, **options):
        created = evaluate_and_send()
        self.stdout.write(self.style.SUCCESS(f"Sent {len(created)} notification(s)."))
