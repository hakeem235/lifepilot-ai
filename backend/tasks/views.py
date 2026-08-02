"""Task API — user-scoped CRUD + segment filtering + check-to-complete.

Every queryset is filtered by the authenticated UserProfile, so one user can
never see or mutate another's tasks (the tenant boundary for this personal app).
"""

from datetime import date

from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Task
from .serializers import TaskSerializer


class TaskViewSet(viewsets.ModelViewSet):
    serializer_class = TaskSerializer

    def get_queryset(self):
        qs = Task.objects.filter(user=self.request.user)
        segment = self.request.query_params.get("segment")
        today = timezone.localdate()
        if segment == "today":
            return qs.filter(status=Task.Status.OPEN, due_date__lte=today)
        if segment == "upcoming":
            return qs.filter(status=Task.Status.OPEN, due_date__gt=today)
        if segment == "completed":
            return qs.filter(status=Task.Status.DONE)
        return qs

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(detail=True, methods=["post"])
    def complete(self, request, pk=None):
        """Toggle a task's completion; persists status/progress/completed_at."""
        task = self.get_object()
        done = request.data.get("done", True)
        task.mark(bool(done))
        task.save(update_fields=["status", "progress", "completed_at"])
        return Response(TaskSerializer(task).data, status=status.HTTP_200_OK)
