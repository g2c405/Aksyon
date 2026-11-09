from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Notification
from .serializers import NotificationSerializer
from users.permissions import IsUser, IsAdmin
from .models import DevicePushToken
from .serializers import DevicePushTokenSerializer
from rest_framework.views import APIView
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

class DevicePushTokenRegisterView(APIView):
    permission_classes = [IsUser]

    def post(self, request):
        print("PUSH REGISTRATION REQUEST:", request.data)

        serializer = DevicePushTokenSerializer(data=request.data)

        if not serializer.is_valid():
            print("PUSH REGISTRATION ERRORS:", serializer.errors)

            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST,
            )

        token = serializer.validated_data["expo_push_token"]

        device, created = DevicePushToken.objects.update_or_create(
            expo_push_token=token,
            defaults={
                "user": request.user,
                "device_id": serializer.validated_data.get(
                    "device_id", ""
                ),
                "platform": serializer.validated_data.get(
                    "platform", "unknown"
                ),
                "is_active": True,
            },
        )

        return Response(
            DevicePushTokenSerializer(device).data,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )


class DevicePushTokenDeactivateView(APIView):
    permission_classes = [IsUser]

    def post(self, request):
        token = request.data.get("expo_push_token")

        if not token:
            return Response(
                {"detail": "expo_push_token is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        updated = DevicePushToken.objects.filter(
            user=request.user,
            expo_push_token=token,
            is_active=True,
        ).update(is_active=False)

        return Response(
            {"detail": "Device token deactivated."},
            status=status.HTTP_200_OK,
        )