from django.contrib import admin

from notifications.models import Notification
from notifications.templates import STATUS_NOTIFICATION_TEMPLATES

from .models import Report


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "user",
        "barangay",
        "status",
        "created_at",
        "resolved_at",
    )

    list_filter = (
        "status",
        "barangay",
    )

    search_fields = (
        "id",
        "user__username",
        "street",
    )

    def save_model(self, request, obj, form, change):
        old_status = None

        if change:
            old_report = Report.objects.get(pk=obj.pk)
            old_status = old_report.status

        super().save_model(request, obj, form, change)

        if not change or old_status == obj.status:
            return

        template = STATUS_NOTIFICATION_TEMPLATES.get(
            obj.status
        )

        if not template:
            return

        Notification.objects.create(
            user=obj.user,
            report=obj,
            **template,
        )