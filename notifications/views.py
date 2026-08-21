from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Notification
from .serializers import NotificationSerializer
from users.permissions import IsUser, IsAdmin

class NotificationViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = NotificationSerializer
    permission_classes = [IsUser]

    def get_queryset(self):
        return (
            Notification.objects
            .filter(user=self.request.user)
            .select_related("report")
            .order_by("-created_at")
        )

    @action(
        detail=True,
        methods=["patch"],
        url_path="read",
    )
    def mark_read(self, request, pk=None):
        notification = self.get_object()

        notification.is_read = True
        notification.save(update_fields=["is_read"])

        return Response(
            self.get_serializer(notification).data,
            status=status.HTTP_200_OK,
        )