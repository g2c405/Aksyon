from django.db import models
from django.contrib.auth import get_user_model
User = get_user_model()
from core.choices import Barangay
from core.choices import Status
# Create your models here.
class Report(models.Model):
    
    user = models.ForeignKey(User, on_delete= models.CASCADE, related_name='reports')
    latitude = models.DecimalField(max_digits=9, decimal_places=6)
    longitude = models.DecimalField(max_digits=9, decimal_places=6)
    barangay = models.CharField(max_length=50, choices=Barangay.choices)
    city = models.CharField(max_length=255, default='Angeles', editable=False)
    description = models.TextField(blank=True)
    media = models.CharField(max_length=255, blank=True)
    media_thumbnail = models.CharField(max_length=500, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    def __str__(self):
        username = self.user.username if self.user else "unknown"
        return f"Report {self.id} by {username}"
    