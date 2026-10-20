from rest_framework import serializers
from .models import Report
from users.serializers import UserSerializer
from .services.storage import create_signed_read_url
from .utils import get_media_type
from .models import Report, PotentialDuplicate

class ReportSerializer(serializers.ModelSerializer):
    description = serializers.CharField(
        max_length=200
    )
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
            "media",
            "media_thumbnail",
            "status",
            "created_at",
            "resolved_at",
        )
        read_only_fields = (
            "user",
            "status",
            "created_at",
            "resolved_at",
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
            "media",
            "media_thumbnail",
            "image_url",
            "video_thumbnail_url",
            "status",
            "created_at",
            "resolved_at",
        )
        read_only_fields = (
            "id",
            "user",
            "city",
            "status",
            "created_at",
            "resolved_at",
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
            "image_url",
            "video_thumbnail_url",
            "status",
            "created_at",
           "resolved_at",
        )
        read_only_fields = (
            "user",
            "status",
            "created_at",
            "resolved_at",
            "city",
            "id",
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


class AdminReportListSerializer(serializers.ModelSerializer):
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
            "image_url",
            "video_thumbnail_url",
            "status",
            "created_at",
            "resolved_at",
        )
        read_only_fields = (
            "user",
            "status",
            "created_at",
            "resolved_at",
            "city",
            "id",
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


class AdminReportDetailSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)

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
            "media",
            "media_thumbnail",
            "status",
            "created_at",
            "resolved_at",
        )


class AdminReportUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Report
        fields = (
            "status",
            "barangay",
        )


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