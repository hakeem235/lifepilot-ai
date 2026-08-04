from rest_framework import serializers

from .models import UserProfile, UserSettings


class UserSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserSettings
        fields = [
            "notifications_enabled",
            "ai_settings",
            "personalization",
            "subscription_tier",
        ]
        read_only_fields = ["subscription_tier"]  # monetization not wired (D6)


class UserProfileSerializer(serializers.ModelSerializer):
    settings = UserSettingsSerializer(read_only=True)

    class Meta:
        model = UserProfile
        fields = [
            "id",
            "email",
            "display_name",
            "avatar_initial",
            "timezone",
            "theme",
            "created_at",
            "settings",
        ]
        read_only_fields = ["id", "email", "created_at"]
