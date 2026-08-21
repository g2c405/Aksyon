from rest_framework import serializers
from .models import Report
from users.serializers import UserSerializer
from .services.storage import create_signed_read_url
from .utils import get_media_type
class ReportSerializer(serializers.ModelSerializer):
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
        )
        read_only_fields = ('user', 'status', 'created_at', 'city', 'id')

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
        )
        read_only_fields = (
            "user",
            "status",
            "created_at",
            "city",
            "id",
            "media_thumbnail_url",
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

class AdminRetrieveReportSerializer(serializers.ModelSerializer):
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
        )
class AdminUpdateReportSerializer(serializers.ModelSerializer):
    class Meta:
        model = Report
        fields = (
            'status',
            'barangay',
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