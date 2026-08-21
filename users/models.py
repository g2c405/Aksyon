from django.db import models
from core.choices import Barangay
# accounts/models.py

from django.contrib.auth.models import AbstractUser
from django.db import models
from core.choices import Role

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

    email_verified = models.BooleanField(default=False)

    def __str__(self):
        return self.username
