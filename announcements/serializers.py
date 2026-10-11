from rest_framework import serializers

from .models import Announcement
from .services.storage import create_signed_read_url
from .utils import get_media_type


class AnnouncementSerializer(serializers.ModelSerializer):
    class Meta:
        model = Announcement
        fields = (
            "id",
            "admin",
            "title",
            "content",
            "barangay",
            "media",
            "media_thumbnail",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "admin",
            "barangay",
            "created_at",
            "updated_at",
        )


class AnnouncementDetailSerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField()
    video_thumbnail_url = serializers.SerializerMethodField()

    class Meta:
        model = Announcement
        fields = (
            "id",
            "admin",
            "title",
            "content",
            "barangay",
            "media",
            "media_thumbnail",
            "image_url",
            "video_thumbnail_url",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields

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


class AnnouncementListSerializer(serializers.ModelSerializer):
    video_thumbnail_url = serializers.SerializerMethodField()
    image_url = serializers.SerializerMethodField()

    class Meta:
        model = Announcement
        fields = (
            "id",
            "title",
            "content",
            "barangay",
            "image_url",
            "video_thumbnail_url",
            "created_at",
            "updated_at",
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

class AnnouncementUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Announcement
        fields = (
            "title",
            "content",
            "media",
            "media_thumbnail",
        )
        