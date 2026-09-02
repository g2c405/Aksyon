from django.urls import path

from .views import (
    AnalyticsDashboardView,
    BarangayAnalyticsDashboardView,
)


urlpatterns = [
    path(
        "dashboard/",
        AnalyticsDashboardView.as_view(),
        name="analytics-dashboard",
    ),
    path(
        "dashboard/barangay/",
        BarangayAnalyticsDashboardView.as_view(),
        name="barangay-analytics-dashboard",
    ),
]