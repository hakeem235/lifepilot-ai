"""Templates API — list system presets + own templates, and apply one to a day.

Applying is the write path: it creates real user-scoped Tasks on the chosen date.
A user can apply any preset (user=None) or one they own, but never another
user's private template.
"""

from django.db.models import Q
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import TaskTemplate
from .serializers import ApplyTemplateSerializer, TaskTemplateSerializer


class TaskTemplateViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = TaskTemplateSerializer

    def get_queryset(self):
        # System presets (user is null) plus the caller's own templates.
        return (
            TaskTemplate.objects.filter(Q(user__isnull=True) | Q(user=self.request.user))
            .prefetch_related("items")
        )

    @action(detail=True, methods=["post"])
    def apply(self, request, pk=None):
        template = self.get_object()
        serializer = ApplyTemplateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        created = serializer.to_created_tasks(template, request.user)
        return Response({"created": created}, status=status.HTTP_201_CREATED)
