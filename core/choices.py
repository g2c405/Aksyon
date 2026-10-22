from django.db import models
class Barangay(models.TextChoices):
    AGAPITO_DEL_ROSARIO = "Agapito del Rosario", "Agapito del Rosario"
    AMSIC = "Amsic", "Amsic"
    ANUNAS = "Anunas", "Anunas"
    BALIBAGO = "Balibago", "Balibago"
    CAPAYA = "Capaya", "Capaya"
    CLARO_M_RECTO = "Claro M. Recto", "Claro M. Recto"
    CUAYAN = "Cuayan", "Cuayan"
    CUTCUT = "Cutcut", "Cutcut"
    CUTUD = "Cutud", "Cutud"
    LOURDES_NORTHWEST = "Lourdes NorthWest", "Lourdes NorthWest"
    LOURDES_SUR = "Lourdes Sur", "Lourdes Sur"
    LOURDES_SUR_EAST = "Lourdes Sur East", "Lourdes Sur East"
    MALABANIAS = "Malabañas", "Malabañas"
    MARGOT = "Margot", "Margot"
    MARISOL = "Marisol", "Marisol"
    MINING = "Mining", "Mining"
    PAMPANG = "Pampang", "Pampang"
    PANDAN = "Pandan", "Pandan"
    PULUNG_BULU = "Pulung Bulu", "Pulung Bulu"
    PULUNG_CACUTUD = "Pulung Cacutud", "Pulung Cacutud"
    PULUNG_MARAGUL = "Pulung Maragul", "Pulung Maragul"
    SALAPUNGAN = "Salapungan", "Salapungan"
    SAN_JOSE = "San José", "San José"
    SAN_NICOLAS = "San Nicolas", "San Nicolas"
    SANTA_TERESITA = "Santa Teresita", "Santa Teresita"
    SANTA_TRINIDAD = "Santa Trinidad", "Santa Trinidad"
    SANTO_CRISTO = "Santo Cristo", "Santo Cristo"
    SANTO_DOMINGO = "Santo Domingo", "Santo Domingo"
    SANTO_ROSARIO = "Santo Rosario", "Santo Rosario"
    SAPALIBUTAD = "Sapalibutad", "Sapalibutad"
    SAPANGBATO = "Sapangbato", "Sapangbato"
    TABUN = "Tabun", "Tabun"
    VIRGEN_DELOS_REMEDIOS = "Virgen Delos Remedios", "Virgen Delos Remedios"

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
    DISMISSED = "dismissed", "Dismissed"

class DuplicateStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    CONFIRMED = "confirmed", "Confirmed"
    DISMISSED = "dismissed", "Dismissed"

class Category(models.TextChoices):
        ROAD_ACCIDENT = 'road_accident', 'Road Accident'
        FIRE = 'fire', 'Fire'
        NATURAL_HAZARD = 'natural_hazard', 'Flooding and Natural Hazards'
        MEDICAL_EMERGENCY = 'medical_emergency', 'Medical Emergency'
        INFRASTRUCTURE_HAZARD = 'infrastructure_hazard', 'Infrastructure Hazard'
        PUBLIC_SAFETY = 'public_safety', 'Public Safety Incident'
        OTHER = 'other', 'Other'

class DismissalReason(models.TextChoices):
    PROFANITY = "profanity", "Profanity in description"
    INCORRECT_BARANGAY = (
        "incorrect_barangay",
        "Incorrect barangay selected",
    )
    INAPPROPRIATE_MEDIA = (
        "inappropriate_media",
        "Inappropriate media evidence",
    )

class AccountSuspensionReason(models.TextChoices):
    INAPPROPRIATE_USER_INFORMATION = (
        "inappropriate_user_information",
        "Inappropriate user information",
    )
    REPORTING_SYSTEM_ABUSE = (
        "reporting_system_abuse",
        "Abuse of the reporting system",
    )
    INAPPROPRIATE_CONTENT = (
        "inappropriate_content",
        "Inappropriate content",
    )
    REPEATED_POLICY_VIOLATIONS = (
        "repeated_policy_violations",
        "Repeated policy violations",
    )
    OTHER = "other", "Other"


class AccountSuspensionDetail(models.TextChoices):
    # Inappropriate user information
    INAPPROPRIATE_FIRST_NAME = (
        "inappropriate_first_name", "Inappropriate first name"
    )
    INAPPROPRIATE_LAST_NAME = (
        "inappropriate_last_name", "Inappropriate last name"
    )
    INAPPROPRIATE_USERNAME = (
        "inappropriate_username", "Inappropriate username"
    )
    INAPPROPRIATE_PROFILE_INFORMATION = (
        "inappropriate_profile_information",
        "Inappropriate profile information",
    )
    FALSE_CONTACT_INFORMATION = (
        "false_contact_information", "False or misleading contact information"
    )

    # Abuse of the reporting system
    FALSE_REPORTS = (
        "false_reports", "Repeated false or fabricated reports"
    )
    MISLEADING_DESCRIPTIONS = (
        "misleading_descriptions", "Deliberately misleading report descriptions"
    )
    SPAM_OR_DUPLICATE_REPORTS = (
        "spam_or_duplicate_reports", "Repeated duplicate or spam reports"
    )
    REPORT_LOCATION_MISUSE = (
        "report_location_misuse", "Deliberate misuse of report locations"
    )

    # Inappropriate content
    PROFANITY_OR_ABUSE = (
        "profanity_or_abuse", "Profanity or abusive language in reports"
    )
    INAPPROPRIATE_MEDIA = (
        "inappropriate_media", "Inappropriate media uploads"
    )
    HARASSMENT_OR_THREATS = (
        "harassment_or_threats", "Harassment or threatening content"
    )

    # Other
    REPEATED_GUIDELINE_VIOLATIONS = (
        "repeated_guideline_violations",
        "Repeated violations of reporting guidelines",
    )
    OTHER_DETAIL = "other_detail", "Other"