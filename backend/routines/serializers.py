from rest_framework import serializers

from tasks.serializers import TaskSerializer

from .models import TaskTemplate, TemplateItem


class TemplateItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = TemplateItem
        fields = ["id", "title", "priority", "order", "time_offset_minutes"]
        read_only_fields = ["id"]


class TaskTemplateSerializer(serializers.ModelSerializer):
    items = TemplateItemSerializer(many=True, read_only=True)
    is_preset = serializers.SerializerMethodField()

    class Meta:
        model = TaskTemplate
        fields = ["id", "name", "icon", "items", "is_preset"]
        read_only_fields = ["id"]

    def get_is_preset(self, obj: TaskTemplate) -> bool:
        return obj.user_id is None


class ApplyTemplateSerializer(serializers.Serializer):
    """Input for POST /api/templates/<id>/apply/ — the day to lay the routine on."""

    date = serializers.DateField()

    def to_created_tasks(self, template: TaskTemplate, user) -> list:
        tasks = template.apply_to(user, self.validated_data["date"])
        return TaskSerializer(tasks, many=True).data
