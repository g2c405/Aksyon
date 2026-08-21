from django.db import models
class Barangay(models.TextChoices):
        STA_TRINIDAD = "Sta. Trinidad", "Sta. Trinidad"
        SAN_NICOLAS = "San Nicolas", "San Nicolas"
        LOURDES_NORTHWEST = "Lourdes NorthWest", "Lourdes NorthWest"
        CLARO_M_RECTO = "Claro M. Recto", "Claro M. Recto"

class NotificationType(models.TextChoices):
    REPORT_UPDATE = "report_update", "Report Update"
    ADMIN_ANNOUNCEMENT = "admin_announcement", "Admin Announcement"
    USER_WARNING = "user_warning", "User Warning"
class Role(models.TextChoices):
        USER = "user", "User"
        ADMIN = "admin", "Admin"
        PRIVILEGED_ADMIN = "privileged_admin", "Privileged Admin"

class Status(models.TextChoices):
    PENDING = "pending", "Pending"
    ONGOING = "ongoing", "Ongoing"
    RESOLVED = "resolved", "Resolved"