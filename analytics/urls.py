from django.urls import path

from .views import (
    AnalyticsDashboardView,
    DBSCANAnalyticsView,
)


urlpatterns = [
    path(
        "dashboard/",
        AnalyticsDashboardView.as_view(),
        name="analytics-dashboard",
    ),
    path(
        "dashboard/dbscan/",
        DBSCANAnalyticsView.as_view(),
        name="analytics-dbscan",
    ),
]