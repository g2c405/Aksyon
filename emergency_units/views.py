
from rest_framework.viewsets import ModelViewSet

from users.permissions import IsAdmin, IsPrivilegedAdmin
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