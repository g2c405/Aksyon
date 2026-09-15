from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    AnnouncementListView,
    AnnouncementDetailView,
    AnnouncementVideoURLView,
    AnnouncementViewSet,
    AnnouncementMediaUploadURLView
)


router = DefaultRouter()

router.register(
    "admin",
    AnnouncementViewSet,
    basename="admin-announcement",
)


urlpatterns = [
    path(
        "",
        AnnouncementListView.as_view(),
        name="announcement-list",
    ),
    path(
        "<int:pk>/",
        AnnouncementDetailView.as_view(),
        name="announcement-detail",
    ),
    path(
        "<int:pk>/video-url/",
        AnnouncementVideoURLView.as_view(),
        name="announcement-video-url",
    ),
    path(
    "admin/media-upload-url/",
    AnnouncementMediaUploadURLView.as_view(),
    name="announcement-media-upload-url",
    ),
    path(
        "",
        include(router.urls),
    ),
]