from django.db import models
from core.choices import Barangay
from django.contrib.auth import get_user_model

User = get_user_model()


class Announcement(models.Model):

    admin = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="announcements",
    )

    barangay = models.CharField(
        max_length=50,
        choices=Barangay.choices,
    )

    title = models.CharField(
        max_length=255,
    )

    content = models.TextField()

    media = models.CharField(
        max_length=255,
        blank=True,
    )

    media_thumbnail = models.CharField(
        max_length=500,
        blank=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    def __str__(self):
        return self.title