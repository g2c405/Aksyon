
from rest_framework.viewsets import ModelViewSet

from users.permissions import IsAdmin, IsPrivilegedAdmin
from .models import EmergencyUnit
from .serializers import EmergencyUnitSerializer


class AdminEmergencyUnitViewSet(ModelViewSet):
    permission_classes = [IsPrivilegedAdmin]
    queryset = EmergencyUnit.objects.all().order_by("name")
    serializer_class = EmergencyUnitSerializer
