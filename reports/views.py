from datetime import timedelta

from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.utils import timezone

from rest_framework import status
from rest_framework.decorators import action
from rest_framework.generics import ListAPIView, RetrieveUpdateAPIView
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet

from .models import Report, PotentialDuplicate
from .serializers import (
    ReportSerializer,
    ReportDetailSerializer,
    ReportListSerializer,
    AdminReportListSerializer,
    AdminReportDetailSerializer,
    AdminReportUpdateSerializer,
    AdminPotentialDuplicateDetailSerializer,
    AdminPotentialDuplicateListSerializer,
    AdminPotentialDuplicateUpdateSerializer,
    NearbyReportSerializer,
)
from .services.storage import create_upload_url, create_signed_read_url
from .utils import get_media_type
from .duplicate_detection import save_potential_duplicates

from emergency_units.services import get_available_responders
from core.geo import find_nearest, haversine
from core.barangays import get_barangay_halls
from core.choices import Status, DuplicateStatus

from notifications.models import Notification
from notifications.templates import STATUS_NOTIFICATION_TEMPLATES

from users.permissions import IsUser, IsAdmin


def create_status_notification(report):
    """Create a notification using the template for the report's current status."""
    template = STATUS_NOTIFICATION_TEMPLATES.get(report.status)

    if not template:
        return

    Notification.objects.create(
        user=report.user,
        report=report,
        **template,
    )


class ReportViewSet(ModelViewSet):
    permission_classes = [IsUser]

    def get_queryset(self):
        reports = Report.objects.filter(user=self.request.user)

        # Hide resolved reports older than 24 hours by default.
        if self.action == "list":
            include_archived = (
                self.request.query_params.get("include_archived") == "true"
            )

            if not include_archived:
                cutoff = timezone.now() - timedelta(hours=24)

                reports = reports.filter(
                    ~Q(status=Status.RESOLVED)
                    | Q(
                        status=Status.RESOLVED,
                        resolved_at__gte=cutoff,
                    )
                )

        return reports.order_by("-created_at")

    def get_serializer_class(self):
        if self.action == "list":
            return ReportListSerializer

        if self.action == "retrieve":
            return ReportDetailSerializer

        return ReportSerializer

    def perform_create(self, serializer):
        report = serializer.save(user=self.request.user)

        save_potential_duplicates(report)
        create_status_notification(report)

    @action(
        detail=True,
        methods=["get"],
        url_path="video-url",
    )
    def video_url(self, request, pk=None):
        report = self.get_object()

        if not report.media or get_media_type(report.media) != "video":
            return Response(
                {"video_url": None},
                status=status.HTTP_200_OK,
            )

        video_url = create_signed_read_url(report.media)

        return Response(
            {"video_url": video_url},
            status=status.HTTP_200_OK,
        )


class AdminListReportView(ListAPIView):
    permission_classes = [IsAdmin]
    serializer_class = AdminReportListSerializer

    def get_queryset(self):
        return Report.objects.filter(
            barangay=self.request.user.assigned_barangay
        ).order_by("-created_at")

    def list(self, request, *args, **kwargs):
        response = super().list(request, *args, **kwargs)

        responders = get_available_responders()
        data = response.data

        # Support both paginated and unpaginated responses.
        reports = (
            data["results"]
            if isinstance(data, dict) and "results" in data
            else data
        )

        for report in reports:
            nearest = None
            distance = None

            if responders:
                accident_location = (
                    float(report["latitude"]),
                    float(report["longitude"]),
                )

                nearest, distance = find_nearest(
                    accident_location,
                    responders,
                )

            report["nearest_responder"] = nearest
            report["distance_km"] = (
                round(distance, 4)
                if distance is not None
                else None
            )

        return response


class AdminPotentialDuplicateListView(ListAPIView):
    permission_classes = [IsAdmin]
    serializer_class = AdminPotentialDuplicateListSerializer

    def get_queryset(self):
        return PotentialDuplicate.objects.filter(
            report__barangay=self.request.user.assigned_barangay,
        ).order_by("-created_at")


class AdminPotentialDuplicateView(RetrieveUpdateAPIView):
    permission_classes = [IsAdmin]

    def get_queryset(self):
        return PotentialDuplicate.objects.filter(
            report__barangay=self.request.user.assigned_barangay,
        )

    def get_serializer_class(self):
        if self.request.method in ["PUT", "PATCH"]:
            return AdminPotentialDuplicateUpdateSerializer

        return AdminPotentialDuplicateDetailSerializer

    @transaction.atomic
    def perform_update(self, serializer):
        old_status = serializer.instance.status
        duplicate = serializer.save()

        # Only perform confirmation actions when the status actually changes.
        if (
            old_status == duplicate.status
            or duplicate.status != DuplicateStatus.CONFIRMED
        ):
            return

        report = duplicate.report
        now = timezone.now()
        update_fields = []

        # Resolve the report when its potential duplicate is confirmed.
        if report.status != Status.RESOLVED:
            report.status = Status.RESOLVED
            update_fields.append("status")

        # Preserve an existing resolution timestamp.
        if report.resolved_at is None:
            report.resolved_at = now
            update_fields.append("resolved_at")

        if update_fields:
            report.save(update_fields=update_fields)

        # Notify the report owner that the report has been resolved.
        create_status_notification(report)


class AdminReportView(RetrieveUpdateAPIView):
    permission_classes = [IsAdmin]

    def get_queryset(self):
        return Report.objects.filter(
            barangay=self.request.user.assigned_barangay
        )

    def get_serializer_class(self):
        if self.request.method in ["PUT", "PATCH"]:
            return AdminReportUpdateSerializer

        return AdminReportDetailSerializer

    @transaction.atomic
    def perform_update(self, serializer):
        old_status = serializer.instance.status
        report = serializer.save()
        now = timezone.now()
        update_fields = []

        if old_status != report.status:
            # Record when the report first enters the ongoing state.
            if (
                report.status == Status.ONGOING
                and report.ongoing_at is None
            ):
                report.ongoing_at = now
                update_fields.append("ongoing_at")

            # Record when the report becomes resolved.
            if (
                report.status == Status.RESOLVED
                and report.resolved_at is None
            ):
                report.resolved_at = now
                update_fields.append("resolved_at")

            # Notify the owner of the new status.
            create_status_notification(report)

        if update_fields:
            report.save(update_fields=update_fields)


class AdminReportVideoURLView(APIView):
    permission_classes = [IsAdmin]

    def get(self, request, pk):
        report = get_object_or_404(
            Report,
            id=pk,
            barangay=request.user.assigned_barangay,
        )

        if not report.media or get_media_type(report.media) != "video":
            return Response(
                {"video_url": None},
                status=status.HTTP_200_OK,
            )

        video_url = create_signed_read_url(report.media)

        return Response(
            {"video_url": video_url},
            status=status.HTTP_200_OK,
        )


class MediaUploadURLView(APIView):
    permission_classes = [IsUser]

    def post(self, request):
        report_id = request.data.get("report_id")

        if not report_id:
            return Response(
                {"error": "report_id is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        report = get_object_or_404(
            Report,
            id=report_id,
            user=request.user,
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

        result = create_upload_url(
            report_id=report.id,
            content_type=content_type,
            extension=allowed_types[content_type],
        )

        return Response(result, status=status.HTTP_200_OK)


class NearbyReportView(APIView):
    permission_classes = [IsUser]

    def get(self, request):
        nearby = []
        data = []

        latitude = request.query_params.get("latitude")
        longitude = request.query_params.get("longitude")

        if not latitude or not longitude:
            return Response(
                {"error": "latitude and longitude are required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            user_location = (float(latitude), float(longitude))
        except (TypeError, ValueError):
            return Response(
                {"error": "Invalid latitude or longitude"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        cutoff = timezone.now() - timedelta(hours=24)

        reports = Report.objects.filter(
            status=Status.ONGOING,
            created_at__gte=cutoff,
        ).exclude(user=request.user)

        for report in reports:
            report_location = (
                float(report.latitude),
                float(report.longitude),
            )

            distance = haversine(
                user_location[0],
                user_location[1],
                report_location[0],
                report_location[1],
            )

            if distance <= 1.0:
                nearby.append((report, distance))

        nearby.sort(key=lambda item: item[1])

        for report, distance in nearby:
            serialized = NearbyReportSerializer(report).data
            serialized["distance_km"] = round(distance, 2)
            data.append(serialized)

        return Response(data)


class NearestBarangayView(APIView):
    permission_classes = [IsUser]

    def post(self, request):
        latitude = request.data.get("latitude")
        longitude = request.data.get("longitude")

        if latitude is None or longitude is None:
            return Response(
                {"error": "latitude and longitude are required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            accident_location = (
                float(latitude),
                float(longitude),
            )
        except (TypeError, ValueError):
            return Response(
                {"error": "Invalid latitude or longitude"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        barangay_halls = get_barangay_halls()

        nearest, distance = find_nearest(
            accident_location,
            barangay_halls,
        )

        return Response({
            "barangay": nearest["barangay"],
            "distance_km": round(distance, 4),
        })
