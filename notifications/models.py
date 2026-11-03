from django.db import models

from django.contrib.auth import get_user_model

User = get_user_model()

from core.choices import NotificationType

from reports.models import Report
from announcements.models import Announcement


class Notification(models.Model):

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="notifications",
    )

    notification_type = models.CharField(
        max_length=50,
        choices=NotificationType.choices,
    )

    report = models.ForeignKey(
        Report,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="notifications",
    )

    announcement = models.ForeignKey(
        Announcement,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="notifications",
    )

    title = models.CharField(max_length=255)

    message = models.TextField()

    is_read = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)


class DevicePushToken(models.Model):

    class Platform(models.TextChoices):
        ANDROID = "android", "Android"
        IOS = "ios", "iOS"
        UNKNOWN = "unknown", "Unknown"

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="push_devices",
    )

    expo_push_token = models.CharField(
        max_length=255,
        unique=True,
    )

    device_id = models.CharField(
        max_length=255,
        blank=True,
        default="",
    )

    platform = models.CharField(
        max_length=20,
        choices=Platform.choices,
        default=Platform.UNKNOWN,
    )

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["user", "is_active"]),
        ]

    def __str__(self):
        return f"{self.user.username} - {self.platform}"