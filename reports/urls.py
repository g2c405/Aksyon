from django.urls import path, include
from .views import (
    ReportViewSet,
    AdminListReportView,
    AdminReportView,
    AdminReportVideoURLView,
    MediaUploadURLView,
    NearbyReportView,
    NearestBarangayView,
)
from rest_framework.routers import DefaultRouter


router = DefaultRouter()

router.register(
    r'user-reports',
    ReportViewSet,
    basename='report'
)


urlpatterns = [
    path('', include(router.urls)),

    path(
        'media/upload-url/',
        MediaUploadURLView.as_view(),
        name='media-upload-url'
    ),

    # Admin report listing
    path(
        'admin/',
        AdminListReportView.as_view(),
        name='admin-report-list'
    ),

    # Admin report retrieval/update
    path(
        'admin/<int:pk>/',
        AdminReportView.as_view(),
        name='admin-report-detail'
    ),

    # Admin actual video URL
    path(
        'admin/<int:pk>/video-url/',
        AdminReportVideoURLView.as_view(),
        name='admin-report-video-url'
    ),

    path(
        'nearby/',
        NearbyReportView.as_view(),
        name='nearby-reports'
    ),

    path(
        'nearest-barangay/',
        NearestBarangayView.as_view(),
        name='nearest-barangay'
    ),
]