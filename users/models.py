from django.db import models
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
