from rest_framework import serializers
from .models import AuditLog


class AuditLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = AuditLog
        fields = [
            "id",
            "actor_username",
            "actor_role",
            "barangay",
            "action",
            "target_type",
            "target_id",
            "description",
            "changes",
            "created_at",
        ]
        read_only_fields = fields