# analytics/views.py

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from django.utils.dateparse import parse_date

from users.permissions import IsAdmin
from reports.models import Report
from core.choices import Barangay

from .services import (
    get_dashboard_summary,
    get_top_reporters,
    get_report_trend,
    get_emergency_categories,
    get_peak_incident_hours,
    get_dbscan_clusters,
)


def get_admin_barangay_reports(request):
    """
    Build a report queryset restricted to the authenticated
    barangay admin's assigned barangay.
    """
    barangay = request.user.assigned_barangay

    if not barangay or barangay not in Barangay.values:
        return None, None

    reports = Report.objects.filter(
        barangay=barangay
    )

    return barangay, reports


class AnalyticsDashboardView(APIView):
    permission_classes = [IsAdmin]

    def get(self, request):
        barangay, reports = get_admin_barangay_reports(request)

        if reports is None:
            return Response(
                {
                    "detail": (
                        "Your account has no valid assigned barangay."
                    )
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        # Read and validate the trend filter.
        period = request.query_params.get(
            "period",
            "all_time",
        )

        allowed_periods = {
            "all_time",
            "past_year",
            "past_month",
            "this_week",
            "today",
            "date_range",
        }

        if period not in allowed_periods:
            return Response(
                {"detail": "Invalid report trend period."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        start_date = None
        end_date = None

        if period == "date_range":
            start_date = parse_date(
                request.query_params.get("start_date", "")
            )
            end_date = parse_date(
                request.query_params.get("end_date", "")
            )

            if not start_date or not end_date:
                return Response(
                    {
                        "detail": (
                            "Valid start_date and end_date are required "
                            "for a custom date range. Use YYYY-MM-DD."
                        )
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            if start_date > end_date:
                return Response(
                    {
                        "detail": (
                            "start_date cannot be later than end_date."
                        )
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

        try:
            summary = get_dashboard_summary(
                reports,
                barangay,
            )

            report_trend = get_report_trend(
                reports,
                period=period,
                start_date=start_date,
                end_date=end_date,
            )

        except ValueError as error:
            return Response(
                {"detail": str(error)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        data = {
            "barangay": barangay,
            **summary,
            "top_reporters": get_top_reporters(reports),
            "report_trend": report_trend,
            "emergency_categories": get_emergency_categories(reports),
            "peak_incident_hours": get_peak_incident_hours(reports),
        }

        return Response(
            data,
            status=status.HTTP_200_OK,
        )



class DBSCANAnalyticsView(APIView):
    permission_classes = [IsAdmin]

    def post(self, request):
        barangay, reports = get_admin_barangay_reports(request)

        if reports is None:
            return Response(
                {
                    "detail": (
                        "Your account has no valid assigned barangay."
                    )
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        data = {
            "barangay": barangay,
            "dbscan_clusters": get_dbscan_clusters(reports),
        }

        return Response(
            data,
            status=status.HTTP_200_OK,
        )
