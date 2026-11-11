from rest_framework.viewsets import ModelViewSet
from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.decorators import action
from django.shortcuts import get_object_or_404
from users.permissions import IsUser, IsAdmin
from django.contrib.auth import get_user_model
from notifications.services import create_notification
User = get_user_model()
from .models import Announcement
from .serializers import (
    AnnouncementSerializer,
    AnnouncementListSerializer,
    AnnouncementUpdateSerializer,
    AnnouncementDetailSerializer,
)
from .services.storage import create_signed_read_url, create_upload_url
from .utils import get_media_type
from notifications.models import Notification
from notifications.templates import ANNOUNCEMENT_NOTIFICATION_TEMPLATE
from django.db import transaction
from audit_logs.services import record_activity
class AnnouncementListView(ListAPIView):
    permission_classes = [IsUser]
    serializer_class = AnnouncementListSerializer

    def get_queryset(self):
        return Announcement.objects.filter(
            barangay=self.request.user.residential_barangay
        ).order_by("-created_at")


class AnnouncementDetailView(RetrieveAPIView):
    permission_classes = [IsUser]
    serializer_class = AnnouncementDetailSerializer

    def get_queryset(self):
        return Announcement.objects.filter(
            barangay=self.request.user.residential_barangay
        )


class AnnouncementVideoURLView(APIView):
    permission_classes = [IsUser]

    def get(self, request, pk):
        announcement = get_object_or_404(
            Announcement,
            id=pk,
            barangay=request.user.residential_barangay,
        )

        if not announcement.media:
            return Response(
                {"video_url": None},
                status=status.HTTP_200_OK,
            )

        media_type = get_media_type(announcement.media)

        if media_type != "video":
            return Response(
                {"video_url": None},
                status=status.HTTP_200_OK,
            )

        video_url = create_signed_read_url(
            announcement.media
        )

        return Response(
            {"video_url": video_url},
            status=status.HTTP_200_OK,
        )


class AnnouncementViewSet(ModelViewSet):
    permission_classes = [IsAdmin]

    def get_queryset(self):
        return Announcement.objects.filter(
            barangay=self.request.user.assigned_barangay
        ).order_by("-created_at")

    def get_serializer_class(self):
        if self.action in ["update", "partial_update"]:
            return AnnouncementUpdateSerializer

        if self.action == "list":
            return AnnouncementListSerializer

        return AnnouncementSerializer

    @transaction.atomic
    def perform_create(self, serializer):
        announcement = serializer.save(
            admin=self.request.user,
            barangay=self.request.user.assigned_barangay,
        )

        users = User.objects.filter(
            residential_barangay=announcement.barangay
        )

        for user in users:
            create_notification(
                user=user,
                announcement=announcement,
                **ANNOUNCEMENT_NOTIFICATION_TEMPLATE,
            )

        record_activity(
            actor=self.request.user,
            action="ANNOUNCEMENT_CREATED",
            target_type="Announcement",
            target_id=announcement.id,
            description=f"Created announcement: {announcement.title}",
            changes={
                "title": announcement.title,
                "barangay": announcement.barangay,
            },
        )

    @transaction.atomic
    def perform_update(self, serializer):
        announcement = serializer.instance

        old_values = {
            "title": announcement.title,
            "content": announcement.content,
            "media": announcement.media,
        }

        announcement = serializer.save()

        changes = {}

        for field, old_value in old_values.items():
            new_value = getattr(announcement, field)

            if old_value != new_value:
                changes[field] = {
                    "from": old_value,
                    "to": new_value,
                }

        if not changes:
            return

        record_activity(
            actor=self.request.user,
            action="ANNOUNCEMENT_UPDATED",
            target_type="Announcement",
            target_id=announcement.id,
            description=f"Updated announcement: {announcement.title}",
            changes=changes,
        )

    @transaction.atomic
    def perform_destroy(self, instance):
        announcement_id = instance.id
        announcement_title = instance.title

        record_activity(
            actor=self.request.user,
            action="ANNOUNCEMENT_DELETED",
            target_type="Announcement",
            target_id=announcement_id,
            description=f"Deleted announcement: {announcement_title}",
            changes={
                "title": announcement_title,
                "barangay": instance.barangay,
            },
        )

        instance.delete()

    @action(
        detail=True,
        methods=["get"],
        url_path="video-url",
    )
    def video_url(self, request, pk=None):
        announcement = self.get_object()

        if not announcement.media:
            return Response(
                {"video_url": None},
                status=status.HTTP_200_OK,
            )

        media_type = get_media_type(announcement.media)

        if media_type != "video":
            return Response(
                {"video_url": None},
                status=status.HTTP_200_OK,
            )

        video_url = create_signed_read_url(
            announcement.media
        )

        return Response(
            {"video_url": video_url},
            status=status.HTTP_200_OK,
        )
class AnnouncementMediaUploadURLView(APIView):
    permission_classes = [IsAdmin]

    def post(self, request):
        announcement_id = request.data.get("announcement_id")

        if not announcement_id:
            return Response(
                {"error": "announcement_id is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        announcement = get_object_or_404(
            Announcement,
            id=announcement_id,
            barangay=request.user.assigned_barangay,
        )

        content_type = request.data.get("content_type")

        if not content_type:
            return Response(
                {"error": "content_type is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        allowed_types = {
            "image/jpeg": "jpg",
            "image/png": "png",
            "image/webp": "webp",
            "video/mp4": "mp4",
            "video/quicktime": "mov",
        }

        if content_type not in allowed_types:
            return Response(
                {"detail": "Unsupported media type."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        extension = allowed_types[content_type]

        result = create_upload_url(
            announcement_id=announcement.id,
            content_type=content_type,
            extension=extension,
        )

        return Response(
            result,
            status=status.HTTP_200_OK,
        )