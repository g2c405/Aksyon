from rest_framework import serializers
from .models import Report, PotentialDuplicate
from users.serializers import UserSerializer
from .services.storage import (
    create_signed_read_url,
    create_signed_read_urls,
)
from .utils import get_media_type
from core.choices import Status, DismissalReason


class ReportListUserSerializer(serializers.Serializer):
    first_name = serializers.CharField(read_only=True)
    last_name = serializers.CharField(read_only=True)


class ReportSerializer(serializers.ModelSerializer):
    description = serializers.CharField(max_length=200)

    class Meta:
        model = Report
        fields = (
            "id",
            "user",
            "latitude",
            "longitude",
            "barangay",
            "city",
            "description",
            "category",
            "media",
            "media_thumbnail",
            "status",
            "created_at",
            "ongoing_at",
            "resolved_at",
            "dismissed_at",
            "dismissal_reason",
        )

        read_only_fields = (
            "user",
            "status",
            "created_at",
            "ongoing_at",
            "resolved_at",
            "dismissed_at",
            "dismissal_reason",
            "city",
            "id",
        )


class ReportDetailSerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField()
    video_thumbnail_url = serializers.SerializerMethodField()

    class Meta:
        model = Report
        fields = (
            "id",
            "user",
            "latitude",
            "longitude",
            "barangay",
            "city",
            "description",
            "category",
            "media",
            "media_thumbnail",
            "image_url",
            "video_thumbnail_url",
            "status",
            "created_at",
            "ongoing_at",
            "resolved_at",
            "resolved_at",
            "dismissed_at",
            "dismissal_reason",
        )
        read_only_fields = (
            "id",
            "user",
            "city",
            "status",
            "created_at",
            "ongoing_at",
            "resolved_at",
            "dismissed_at",
            "dismissal_reason",
            "image_url",
            "video_thumbnail_url",
        )

    def get_image_url(self, obj):
        if get_media_type(obj.media) != "image":
            return None

        return create_signed_read_url(obj.media)

    def get_video_thumbnail_url(self, obj):
        if get_media_type(obj.media) != "video":
            return None

        if not obj.media_thumbnail:
            return None

        return create_signed_read_url(obj.media_thumbnail)


class ReportListBatchSerializer(serializers.ListSerializer):
    def to_representation(self, data):
        reports = list(data)

        paths = []

        for report in reports:
            media_type = get_media_type(report.media)

            if media_type == "image" and report.media:
                paths.append(report.media)

            elif (
                media_type == "video"
                and report.media_thumbnail
            ):
                paths.append(report.media_thumbnail)

        signed_urls = create_signed_read_urls(paths)

        self.child.context["batch_signed_urls"] = signed_urls

        return [
            self.child.to_representation(report)
            for report in reports
        ]


class ReportListSerializer(serializers.ModelSerializer):
    video_thumbnail_url = serializers.SerializerMethodField()
    image_url = serializers.SerializerMethodField()

    class Meta:
        model = Report
        fields = (
            "id",
            "user",
            "latitude",
            "longitude",
            "barangay",
            "city",
            "description",
            "category",
            "image_url",
            "video_thumbnail_url",
            "status",
            "created_at",
            "ongoing_at",
            "resolved_at",
            "dismissed_at",
            "dismissal_reason",
        )

        read_only_fields = (
            "user",
            "status",
            "created_at",
            "ongoing_at",
            "resolved_at",
            "dismissed_at",
            "dismissal_reason",
            "city",
            "id",
        )

        list_serializer_class = ReportListBatchSerializer

    def get_image_url(self, obj):
        if get_media_type(obj.media) != "image":
            return None

        signed_urls = self.context.get("batch_signed_urls", {})

        return signed_urls.get(obj.media)

    def get_video_thumbnail_url(self, obj):
        if get_media_type(obj.media) != "video":
            return None

        if not obj.media_thumbnail:
            return None

        signed_urls = self.context.get("batch_signed_urls", {})

        return signed_urls.get(obj.media_thumbnail)
    
class AdminReportListSerializer(serializers.ModelSerializer):
    user = ReportListUserSerializer(read_only=True)

    class Meta:
        model = Report
        fields = (
            "id",
            "user",
            "latitude",
            "longitude",
            "barangay",
            "city",
            "description",
            "category",
            "status",
            "created_at",
            "ongoing_at",
            "resolved_at",
            "dismissed_at",
            "dismissal_reason",
        )

        read_only_fields = (
            "id",
            "user",
            "status",
            "created_at",
            "ongoing_at",
            "resolved_at",
            "dismissed_at",
            "dismissal_reason",
            "city",
        )


class AdminReportDetailSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    image_url = serializers.SerializerMethodField()
    video_thumbnail_url = serializers.SerializerMethodField()

    class Meta:
        model = Report
        fields = (
            "id",
            "user",
            "latitude",
            "longitude",
            "barangay",
            "city",
            "description",
            "category",
            "media",
            "media_thumbnail",
            "image_url",
            "video_thumbnail_url",
            "status",
            "created_at",
            "ongoing_at",
            "resolved_at",
            "dismissed_at",
            "dismissal_reason",
        )

    def get_image_url(self, obj):
        if get_media_type(obj.media) != "image":
            return None

        return create_signed_read_url(obj.media)

    def get_video_thumbnail_url(self, obj):
        if get_media_type(obj.media) != "video":
            return None

        if not obj.media_thumbnail:
            return None

        return create_signed_read_url(obj.media_thumbnail)


class AdminReportUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Report
        fields = (
            "status",
            "barangay",
            "dismissal_reason",
        )

    def validate(self, attrs):
        status_value = attrs.get(
            "status",
            self.instance.status if self.instance else None,
        )
        dismissal_reason = attrs.get(
            "dismissal_reason",
            self.instance.dismissal_reason if self.instance else None,
        )

        if status_value == Status.DISMISSED and not dismissal_reason:
            raise serializers.ValidationError({
                "dismissal_reason": (
                    "A dismissal reason is required when dismissing a report."
                )
            })

        if (
            status_value != Status.DISMISSED
            and "dismissal_reason" in attrs
            and dismissal_reason
        ):
            raise serializers.ValidationError({
                "dismissal_reason": (
                    "A dismissal reason can only be set for dismissed reports."
                )
            })

        return attrs


class NearbyReportSerializer(serializers.ModelSerializer):
    media_thumbnail_url = serializers.SerializerMethodField()

    class Meta:
        model = Report
        fields = (
            "id",
            "media_thumbnail_url",
            "status",
            "created_at",
        )

    def get_media_thumbnail_url(self, obj):
        if not obj.media_thumbnail:
            return None

        return create_signed_read_url(obj.media_thumbnail)


class AdminPotentialDuplicateListSerializer(serializers.ModelSerializer):
    report = AdminReportListSerializer(read_only=True)
    potential_duplicate = AdminReportListSerializer(read_only=True)

    class Meta:
        model = PotentialDuplicate
        fields = (
            "id",
            "report",
            "potential_duplicate",
            "distance_meters",
            "time_difference_seconds",
            "barangay_match",
            "description_similarity",
            "similarity_score",
            "status",
            "created_at",
        )


class AdminPotentialDuplicateDetailSerializer(serializers.ModelSerializer):
    report = AdminReportDetailSerializer(read_only=True)
    potential_duplicate = AdminReportDetailSerializer(read_only=True)

    class Meta:
        model = PotentialDuplicate
        fields = (
            "id",
            "report",
            "potential_duplicate",
            "distance_meters",
            "time_difference_seconds",
            "barangay_match",
            "description_similarity",
            "similarity_score",
            "status",
            "created_at",
        )


class AdminPotentialDuplicateUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = PotentialDuplicate
        fields = (
            "status",
        )
