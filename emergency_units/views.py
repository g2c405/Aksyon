
from django.db import transaction
from rest_framework.viewsets import ModelViewSet

from users.permissions import IsAdmin, IsPrivilegedAdmin
from audit_logs.services import record_activity

from .models import EmergencyUnit
from .serializers import EmergencyUnitSerializer


class AdminEmergencyUnitViewSet(ModelViewSet):
    queryset = EmergencyUnit.objects.all().order_by("name")
    serializer_class = EmergencyUnitSerializer

    def get_permissions(self):
        if self.action in ["list", "retrieve"]:
            permission_classes = [IsAdmin]
        else:
            permission_classes = [IsPrivilegedAdmin]

        return [permission() for permission in permission_classes]

    @transaction.atomic
    def perform_create(self, serializer):
        unit = serializer.save()

        record_activity(
            actor=self.request.user,
            action="EMERGENCY_UNIT_CREATED",
            target_type="EmergencyUnit",
            target_id=unit.pk,
            description=f"Created emergency unit: {unit.name}.",
            changes=dict(serializer.data),
        )

    @transaction.atomic
    def perform_update(self, serializer):
        instance = serializer.instance
        old_data = dict(self.get_serializer(instance).data)

        unit = serializer.save()

        new_data = dict(self.get_serializer(unit).data)

        changes = {
            field: {
                "old": old_data[field],
                "new": new_data[field],
            }
            for field in old_data
            if old_data[field] != new_data.get(field)
        }

        if changes:
            record_activity(
                actor=self.request.user,
                action="EMERGENCY_UNIT_UPDATED",
                target_type="EmergencyUnit",
                target_id=unit.pk,
                description=f"Updated emergency unit: {unit.name}.",
                changes=changes,
            )

    @transaction.atomic
    def perform_destroy(self, instance):
        unit_id = instance.pk
        unit_name = instance.name
        old_data = dict(self.get_serializer(instance).data)

        record_activity(
            actor=self.request.user,
            action="EMERGENCY_UNIT_DELETED",
            target_type="EmergencyUnit",
            target_id=unit_id,
            description=f"Deleted emergency unit: {unit_name}.",
            changes=old_data,
        )

        instance.delete()
