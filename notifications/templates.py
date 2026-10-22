
from core.choices import Status
from core.choices import Status, DismissalReason
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

ANNOUNCEMENT_NOTIFICATION_TEMPLATE = {
    "notification_type": "admin_announcement",
    "title": "New barangay announcement",
    "message": (
        "Your barangay has posted a new announcement."
    ),
}

DISMISSAL_NOTIFICATION_TEMPLATES = {
    DismissalReason.PROFANITY: {
        "notification_type": "user_warning",
        "title": "Report dismissed",
        "message": (
            "Your report was dismissed because its description "
            "contains profanity."
        ),
    },
    DismissalReason.INCORRECT_BARANGAY: {
        "notification_type": "user_warning",
        "title": "Report dismissed",
        "message": (
            "Your report was dismissed because the selected "
            "barangay was incorrect. Please submit it to the "
            "appropriate barangay."
        ),
    },
    DismissalReason.INAPPROPRIATE_MEDIA: {
        "notification_type": "user_warning",
        "title": "Report dismissed",
        "message": (
            "Your report was dismissed because the attached "
            "media evidence was inappropriate."
        ),
    },
}