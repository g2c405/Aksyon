from django.db import models
from django.conf import settings
from core.choices import (
    Role,
    Barangay,
    AccountSuspensionReason,
    AccountSuspensionDetail,
)
# accounts/models.py

from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    email = models.EmailField(unique=True)
    contact_number = models.CharField(
        max_length=20,
        blank=True,
        null=True,
    )
    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.USER,
    )
    residential_barangay = models.CharField(
    max_length=100,
    choices=Barangay.choices,
    null=True,
    blank=True,
    )

    assigned_barangay = models.CharField(
    max_length=100,
    choices=Barangay.choices,
    null=True,
    blank=True,
    )

    suspension_reason = models.CharField(
        max_length=50,
        choices=AccountSuspensionReason.choices,
        blank=True,
        default="",
    )

    suspension_detail = models.CharField(
        max_length=50,
        choices=AccountSuspensionDetail.choices,
        blank=True,
        default="",
    )

    suspension_notes = models.TextField(
        blank=True,
        default="",
        max_length=200
    )

    suspended_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    reactivated_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    email_verified = models.BooleanField(default=False)

    def __str__(self):
        return self.username

class EmailVerificationOTP(models.Model):

    class Purpose(models.TextChoices):
        REGISTRATION = "registration", "Registration"
        EMAIL_CHANGE = "email_change", "Email Change"
        CONTACT_CHANGE = "contact_change", "Contact Number Change"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="verification_otps",
    )

    purpose = models.CharField(
        max_length=20,
        choices=Purpose.choices,
    )

    # Store the hashed OTP, never the actual numeric code.
    code_hash = models.CharField(max_length=128)

    # Used for pending email addresses or contact numbers.
    target_value = models.CharField(
        max_length=254,
        blank=True,
        default="",
    )

    created_at = models.DateTimeField(auto_now_add=True)

    expires_at = models.DateTimeField()

    consumed_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    attempts = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "purpose"]),
        ]

    def __str__(self):
        return f"{self.user.username} - {self.purpose}"