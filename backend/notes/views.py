"""Note API — user-scoped CRUD with optional search.

Every queryset filters by the authenticated UserProfile, so one user can never
read or mutate another's notes.
"""

from rest_framework import viewsets

from .models import Note
from .serializers import NoteSerializer


class NoteViewSet(viewsets.ModelViewSet):
    serializer_class = NoteSerializer

    def get_queryset(self):
        qs = Note.objects.filter(user=self.request.user)
        search = (self.request.query_params.get("q") or "").strip()
        if search:
            # Title and body, case-insensitive. Postgres-friendly and index-free;
            # good enough for a personal note count, not a search engine.
            from django.db.models import Q

            qs = qs.filter(Q(title__icontains=search) | Q(body__icontains=search))
        if self.request.query_params.get("pinned") == "true":
            qs = qs.filter(pinned=True)
        return qs

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
