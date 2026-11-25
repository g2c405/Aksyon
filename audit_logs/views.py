from rest_framework.generics import ListAPIView, RetrieveAPIView

from users.permissions import IsPrivilegedAdmin
from .models import AuditLog
from .serializers import AuditLogSerializer
from core.pagination import StandardResultsSetPagination

class AuditLogListView(ListAPIView):
    permission_classes = [IsPrivilegedAdmin]
    serializer_class = AuditLogSerializer
    queryset = AuditLog.objects.all().order_by("-created_at")
    pagination_class = StandardResultsSetPagination


class AuditLogDetailView(RetrieveAPIView):
    permission_classes = [IsPrivilegedAdmin]
    serializer_class = AuditLogSerializer

    queryset = AuditLog.objects.all()