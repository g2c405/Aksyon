
from django.db import models


class EmergencyUnit(models.Model):
    class UnitType(models.TextChoices):
        HOSPITAL = "hospital", "Hospital"
        POLICE = "police", "Police Department"
        FIRE = "fire", "Fire Department"

    name = models.CharField(max_length=255)
    unit_type = models.CharField(
        max_length=20,
        choices=UnitType.choices,
    )
    address = models.CharField(
        max_length=255,
        blank=True,
        null=True,
    )
    latitude = models.FloatField()
    longitude = models.FloatField()
    contact_number = models.CharField(max_length=20)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.name} ({self.unit_type})"
