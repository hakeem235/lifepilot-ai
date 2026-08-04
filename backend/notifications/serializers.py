from rest_framework import serializers

from .models import Notification


class NotificationSerializer(serializers.ModelSerializer):
    read = serializers.SerializerMethodField()

    class Meta:
        model = Notification
        fields = ["id", "kind", "title", "body", "task", "created_at", "read"]

    def get_read(self, obj: Notification) -> bool:
        return obj.read_at is not None
