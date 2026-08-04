from rest_framework import serializers

from .models import Task


class TaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = Task
        fields = [
            "id",
            "title",
            "notes",
            "due_date",
            "priority",
            "status",
            "progress",
            "source",
            "created_at",
            "completed_at",
        ]
        read_only_fields = ["id", "created_at", "completed_at"]

    def validate_progress(self, value: int) -> int:
        if not 0 <= value <= 100:
            raise serializers.ValidationError("progress must be between 0 and 100.")
        return value
