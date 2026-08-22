from .models import Report
from .serializers import ReportSerializer, AdminRetrieveReportSerializer, ReportListSerializer, AdminUpdateReportSerializer
from rest_framework.viewsets import ModelViewSet
from rest_framework.generics import ListAPIView, RetrieveUpdateAPIView
from rest_framework.views import APIView
from rest_framework import permissions
from rest_framework.response import Response
from rest_framework import status
from .services.storage import create_upload_url
from django.shortcuts import get_object_or_404
#from emergency_units.services import get_available_responders
from core.geo import find_nearest
from core.barangays import get_barangay_halls
from datetime import timedelta
from django.utils import timezone
from core.geo import haversine
from .serializers import NearbyReportSerializer
from rest_framework.decorators import action
from .services.storage import create_signed_read_url
from .utils import get_media_type
from datetime import timedelta
from django.utils import timezone
from django.db.models import Q
from notifications.models import Notification
from users.permissions import IsUser, IsAdmin
from notifications.templates import STATUS_NOTIFICATION_TEMPLATES
from core.choices import Status
class ReportViewSet(ModelViewSet):
    permission_classes = [IsUser]

    def get_queryset(self):
        now = timezone.now()
        cutoff = now - timedelta(hours=24)
        return (
            Report.objects
            .filter(
                ~Q(status=Status.RESOLVED) |
                Q(
                    status=Status.RESOLVED,
                    resolved_at__gte=cutoff,
                )
            )
            .order_by("-created_at")
        )

    def get_serializer_class(self):
        if self.action == "list":
            return ReportListSerializer

        return ReportSerializer

    def perform_create(self, serializer):
        report = serializer.save(user=self.request.user)
        template = STATUS_NOTIFICATION_TEMPLATES.get(report.status)

        Notification.objects.create(
        user=report.user,
        report=report,
        **template
    )

    @action(
        detail=True,
        methods=['get'],
        url_path='video-url'
    )
    def video_url(self, request, pk=None):
        report = self.get_object()
        if not report.media:
            return Response({"video_url": None}, status=status.HTTP_200_OK)
        media_type = get_media_type(report.media)

        if media_type != "video":
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
    serializer_class = AdminRetrieveReportSerializer
    def get_queryset(self):
        return Report.objects.filter(
            barangay=self.request.user.assigned_barangay
        ).order_by("-created_at")

class AdminReportView(RetrieveUpdateAPIView):
    permission_classes = [IsAdmin]

    def get_queryset(self):
        return Report.objects.filter(
            barangay=self.request.user.assigned_barangay
        )

    def get_serializer_class(self):
        if self.request.method in ["PUT", "PATCH"]:
            return AdminUpdateReportSerializer

        return AdminRetrieveReportSerializer

    def perform_update(self, serializer):
        old_status = serializer.instance.status

        report = serializer.save()

        if old_status == report.status:
            return

        # Set resolved_at when the report becomes resolved.
        if report.status == Report.Status.RESOLVED:
            report.resolved_at = timezone.now()
            report.save(update_fields=["resolved_at"])

        template = STATUS_NOTIFICATION_TEMPLATES.get(
            report.status
        )

        if not template:
            return

        Notification.objects.create(
            user=report.user,
            report=report,
            **template,
        )

class MediaUploadURLView(APIView):
    permission_classes = [IsUser]

    def post(self, request):
        print("===== MEDIA UPLOAD URL REQUEST =====")
        print("REQUEST DATA:", request.data)
        print("USER:", request.user)
        print("USER ID:", request.user.id)
        report_id = request.data.get("report_id")
        print("REPORT ID:", report_id)
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
        print("CONTENT TYPE:", content_type)
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
        print("REPORT VERIFIED:", report.id)
        print("REPORT OWNER:", report.user.id)
        print("ALLOWED EXTENSION:", extension)
        result = create_upload_url(
            report_id=report.id,
            content_type=content_type,
            extension=extension,
        )
        print("SIGNED URL RESULT:", result)
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

        cutoff = timezone.now() - timedelta(hours=24)

        reports = Report.objects.filter(
            status=Report.Status.ONGOING,
            created_at__gte=cutoff,
        ).exclude(
            user=request.user
        )

        user_location = (float(latitude), float(longitude))

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

        nearby.sort(key=lambda x: x[1])

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
