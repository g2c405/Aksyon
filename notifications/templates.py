
from core.choices import Status

STATUS_NOTIFICATION_TEMPLATES = {
    Status.PENDING: {
            "notification_type": "report_update",
            "title": "Report has been submitted",
            "message": (
                "Your report has been submitted and is under review."
            ),
    },
    Status.ONGOING: {
        "notification_type": "report_update",
        "title": "Report is now being handled",
        "message": (
            "Your report is now being handled by the barangay."
        ),
    },
    Status.RESOLVED: {
        "notification_type": "report_update",
        "title": "Report resolved",
        "message": (
            "Your reported issue has been marked as resolved."
        ),
    },
}