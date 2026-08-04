"""Notifications API — device registration + the in-app center.

All endpoints are user-scoped: a user only ever sees or mutates their own
notifications and device tokens.
"""

from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import DeviceToken, Notification
from .serializers import NotificationSerializer


class RegisterDeviceView(APIView):
    def post(self, request):
        token = (request.data.get("token") or "").strip()
        if not token:
            return Response({"detail": "token is required."}, status=status.HTTP_400_BAD_REQUEST)
        # Reassign the token to this user (a device may be shared across logins).
        DeviceToken.objects.update_or_create(
            token=token,
            defaults={"user": request.user, "platform": request.data.get("platform", "")},
        )
        return Response(status=status.HTTP_204_NO_CONTENT)


class NotificationViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = NotificationSerializer

    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user)

    def list(self, request, *args, **kwargs):
        qs = self.get_queryset()
        data = NotificationSerializer(qs, many=True).data
        unread = qs.filter(read_at__isnull=True).count()
        return Response({"notifications": data, "unread": unread})

    @action(detail=True, methods=["post"])
    def read(self, request, pk=None):
        notif = self.get_object()
        if notif.read_at is None:
            notif.read_at = timezone.now()
            notif.save(update_fields=["read_at"])
        return Response(NotificationSerializer(notif).data)

    @action(detail=False, methods=["post"], url_path="read-all")
    def read_all(self, request):
        self.get_queryset().filter(read_at__isnull=True).update(read_at=timezone.now())
        return Response(status=status.HTTP_204_NO_CONTENT)
