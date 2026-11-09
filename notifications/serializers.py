from rest_framework import serializers
from .models import Notification, DevicePushToken
class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = (
            "id",
            "notification_type",
            "report",
            "announcement",
            "title",
            "message",
            "is_read",
            "created_at",
        )
        read_only_fields = (
            "id",
            "notification_type",
            "announcement",
            "report",
            "title",
            "message",
            "created_at",
        )

class DevicePushTokenSerializer(serializers.ModelSerializer):

    class Meta:
        model = DevicePushToken
        fields = (
            "id",
            "expo_push_token",
            "device_id",
            "platform",
            "is_active",
        )
        read_only_fields = (
            "id",
            "is_active",
        )
        extra_kwargs = {
            "expo_push_token": {
                "validators": [],
            },
        }