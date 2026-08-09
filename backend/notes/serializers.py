from rest_framework import serializers

from .models import Note


class NoteSerializer(serializers.ModelSerializer):
    display_title = serializers.CharField(read_only=True)

    class Meta:
        model = Note
        fields = [
            "id",
            "title",
            "body",
            "display_title",
            "pinned",
            "source",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "display_title", "created_at", "updated_at"]

    def validate(self, attrs):
        """Refuse a note that is entirely empty.

        Checked across the merged state, not the payload alone, so a PATCH that
        blanks the body of an untitled note is rejected too — otherwise a note
        could become invisible in the list with no way back to it.
        """
        title = attrs.get("title", getattr(self.instance, "title", "") or "")
        body = attrs.get("body", getattr(self.instance, "body", "") or "")
        if not title.strip() and not body.strip():
            raise serializers.ValidationError("A note needs a title or a body.")
        return attrs
