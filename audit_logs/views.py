from rest_framework.generics import ListAPIView, RetrieveAPIView

from users.permissions import IsPrivilegedAdmin
from .models import AuditLog
from .serializers import AuditLogSerializer


class AuditLogListView(ListAPIView):
    permission_classes = [IsPrivilegedAdmin]
    serializer_class = AuditLogSerializer

    queryset = AuditLog.objects.all().order_by("-created_at")


class AuditLogDetailView(RetrieveAPIView):
    permission_classes = [IsPrivilegedAdmin]
    serializer_class = AuditLogSerializer

    queryset = AuditLog.objects.all()