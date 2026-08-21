from django.db import models
from django.contrib.auth import get_user_model
User = get_user_model()
from reports.models import Report
class Notification(models.Model):

    class NotificationType(models.TextChoices):
        REPORT_STATUS = "report_status", "Report Status"
        USER_WARNING = "user_warning", "User Warning"
        SYSTEM = "system", "System"
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
    title = models.CharField(max_length=255)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
