
from datetime import timedelta

import numpy as np
from django.db.models import Count
from django.utils.timezone import localdate, now
from sklearn.cluster import DBSCAN

from reports.models import Report, PotentialDuplicate
from core.choices import Status, Barangay, DuplicateStatus


def get_analytics_reports(queryset=None):
    """
    Return reports eligible for analytics.

    Excludes reports marked as confirmed duplicates.
    Pending and rejected potential duplicates remain included.
    """
    reports = queryset if queryset is not None else Report.objects.all()

    confirmed_duplicate_report_ids = (
        PotentialDuplicate.objects.filter(
            status=DuplicateStatus.CONFIRMED
        ).values("report_id")
    )

    return reports.exclude(
        id__in=confirmed_duplicate_report_ids
    )


def get_basic_report_stats(queryset=None):
    reports = get_analytics_reports(queryset)

    return {
        "total_reports": reports.count(),
        "pending": reports.filter(status=Status.PENDING).count(),
        "ongoing": reports.filter(status=Status.ONGOING).count(),
        "resolved": reports.filter(status=Status.RESOLVED).count(),
    }


def get_top_reporters(queryset=None, limit=10):
    reports = get_analytics_reports(queryset)

    return list(
        reports
        .values("user__username")
        .annotate(total=Count("id"))
        .order_by("-total")[:limit]
    )


def get_reports_last_7_days(queryset=None):
    reports = get_analytics_reports(queryset)

    start_date = now() - timedelta(days=7)

    return reports.filter(
        created_at__gte=start_date
    ).count()


def get_reports_by_barangay(queryset=None):
    reports = get_analytics_reports(queryset)

    data = (
        reports
        .values("barangay")
        .annotate(total=Count("id"))
        .order_by("-total")
    )

    return {
        item["barangay"]: item["total"]
        for item in data
    }


def get_reports_by_barangay_with_details(queryset=None):
    reports = get_analytics_reports(queryset)

    return {
        barangay: list(
            reports
            .filter(barangay=barangay)
            .values()
        )
        for barangay in Barangay.values
    }


def get_reports_by_hour(queryset=None):
    reports = get_analytics_reports(queryset)

    hourly = {i: 0 for i in range(24)}

    for report in reports:
        hour = report.created_at.hour
        hourly[hour] += 1

    return hourly


def get_dbscan_clusters(
    queryset=None,
    eps_km=0.5,
    min_samples=2,
):
    reports = get_analytics_reports(queryset).values(
        "id",
        "latitude",
        "longitude",
    )

    reports = list(reports)

    if not reports:
        return []

    coords = np.array([
        [
            float(report["latitude"]),
            float(report["longitude"]),
        ]
        for report in reports
    ])

    kms_per_radian = 6371.0088
    epsilon = eps_km / kms_per_radian

    model = DBSCAN(
        eps=epsilon,
        min_samples=min_samples,
        algorithm="ball_tree",
        metric="haversine",
    ).fit(np.radians(coords))

    labels = model.labels_

    results = []

    for report, label in zip(reports, labels):
        results.append({
            "id": report["id"],
            "latitude": report["latitude"],
            "longitude": report["longitude"],
            "cluster": int(label),
        })

    return results


def get_report_trend(queryset=None):
    reports = get_analytics_reports(queryset)

    today = localdate()
    start_date = today - timedelta(days=6)

    trend = {
        str(start_date + timedelta(days=i)): 0
        for i in range(7)
    }

    reports = reports.filter(
        created_at__date__gte=start_date,
        created_at__date__lte=today,
    )

    for report in reports:
        date = str(
            report.created_at.astimezone().date()
        )
        trend[date] += 1

    return trend
