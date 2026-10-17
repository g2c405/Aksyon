
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from users.permissions import IsAdmin
from reports.models import Report
from core.choices import Barangay

from .services import (
    get_basic_report_stats,
    get_top_reporters,
    get_reports_last_7_days,
    get_reports_by_barangay,
    get_reports_by_barangay_with_details,
    get_dbscan_clusters,
    get_reports_by_hour,
)


class AnalyticsDashboardView(APIView):
    permission_classes = [IsAdmin]

    def get(self, request):
        data = {
            "basic_stats": get_basic_report_stats(),
            "top_reporters": get_top_reporters(),
            "reports_last_7_days": get_reports_last_7_days(),
            "reports_by_barangay": get_reports_by_barangay(),
            "reports_by_barangay_with_details":
                get_reports_by_barangay_with_details(),
            "dbscan_clusters": get_dbscan_clusters(),
            "reports_by_hour": get_reports_by_hour(),
        }

        return Response(data, status=status.HTTP_200_OK)


class BarangayAnalyticsDashboardView(APIView):
    permission_classes = [IsAdmin]

    def get(self, request):
        barangay = request.query_params.get("barangay")

        if not barangay:
            return Response(
                {"detail": "barangay query parameter is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if barangay not in Barangay.values:
            return Response(
                {"detail": "Invalid barangay."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        reports = Report.objects.filter(barangay=barangay)

        data = {
            "barangay": barangay,
            "basic_stats": get_basic_report_stats(reports),
            "top_reporters": get_top_reporters(reports),
            "reports_last_7_days":
                get_reports_last_7_days(reports),
            "reports_by_barangay":
                get_reports_by_barangay(reports),
            "reports_by_barangay_with_details":
                get_reports_by_barangay_with_details(reports),
            "dbscan_clusters":
                get_dbscan_clusters(reports),
            "reports_by_hour":
                get_reports_by_hour(reports),
        }

        return Response(data, status=status.HTTP_200_OK)
