
from django.conf import settings
from django.db import models


class AuditLog(models.Model):
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_logs",
    )

    # Preserve administrator information even if their account changes.
    actor_username = models.CharField(max_length=150)
    actor_role = models.CharField(max_length=50)
    barangay = models.CharField(
        max_length=100,
        null=True,
        blank=True,
    )

    # What action was performed?
    action = models.CharField(max_length=100)

    # What record was affected?
    target_type = models.CharField(max_length=100)
    target_id = models.CharField(
        max_length=100,
        null=True,
        blank=True,
    )

    description = models.TextField(blank=True)

    # Optional before-and-after values.
    changes = models.JSONField(default=dict, blank=True)

    created_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
    )

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Audit Log"
        verbose_name_plural = "Audit Logs"

    def __str__(self):
        return f"{self.actor_username} - {self.action}"
