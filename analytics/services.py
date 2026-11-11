# analytics/services.py

from datetime import date, datetime, time, timedelta

import numpy as np

from django.contrib.auth import get_user_model
from django.db.models import Count, Q, Min
from django.db.models.functions import (
    ExtractHour,
    TruncHour,
    TruncDate,
    TruncWeek,
    TruncMonth,
    TruncYear,
)
from django.utils import timezone

from sklearn.cluster import DBSCAN

from reports.models import Report, PotentialDuplicate
from core.choices import (
    Role,
    Status,
    Category,
    DuplicateStatus,
)

User = get_user_model()


def get_analytics_reports(queryset):
    """
    Return reports from the supplied queryset, excluding
    reports marked as confirmed duplicates.
    """
    confirmed_duplicate_report_ids = (
        PotentialDuplicate.objects
        .filter(status=DuplicateStatus.CONFIRMED)
        .values("report_id")
    )

    return queryset.exclude(
        id__in=confirmed_duplicate_report_ids
    )


def get_dashboard_summary(queryset, barangay):
    """
    Return report totals, today's statuses, overall statuses,
    and resident totals for one assigned barangay.

    Report statistics use one database aggregation.
    Resident totals use one separate database query.
    """
    today = timezone.localdate()

    reports = get_analytics_reports(queryset)

    today_start = timezone.make_aware(
        datetime.combine(today, time.min)
    )
    tomorrow_start = timezone.make_aware(
        datetime.combine(today + timedelta(days=1), time.min)
    )

    report_stats = reports.aggregate(
        total_reports=Count("id"),

        total_pending=Count(
            "id",
            filter=Q(status=Status.PENDING),
        ),
        total_ongoing=Count(
            "id",
            filter=Q(status=Status.ONGOING),
        ),
        total_resolved=Count(
            "id",
            filter=Q(status=Status.RESOLVED),
        ),
        total_dismissed=Count(
            "id",
            filter=Q(status=Status.DISMISSED),
        ),

        today_pending=Count(
            "id",
            filter=Q(
                status=Status.PENDING,
                created_at__gte=today_start,
                created_at__lt=tomorrow_start,
            ),
        ),
        today_ongoing=Count(
            "id",
            filter=Q(
                status=Status.ONGOING,
                created_at__gte=today_start,
                created_at__lt=tomorrow_start,
            ),
        ),
        today_resolved=Count(
            "id",
            filter=Q(
                status=Status.RESOLVED,
                created_at__gte=today_start,
                created_at__lt=tomorrow_start,
            ),
        ),
        today_dismissed=Count(
            "id",
            filter=Q(
                status=Status.DISMISSED,
                created_at__gte=today_start,
                created_at__lt=tomorrow_start,
            ),
        ),
    )

    total_users = User.objects.filter(
        role=Role.USER,
        residential_barangay=barangay,
    ).count()

    return {
        "totals": {
            "total_reports": report_stats["total_reports"],
            "total_users": total_users,
        },
        "today_statuses": {
            "pending": report_stats["today_pending"],
            "ongoing": report_stats["today_ongoing"],
            "resolved": report_stats["today_resolved"],
            "dismissed": report_stats["today_dismissed"],
        },
        "total_statuses": {
            "pending": report_stats["total_pending"],
            "ongoing": report_stats["total_ongoing"],
            "resolved": report_stats["total_resolved"],
            "dismissed": report_stats["total_dismissed"],
        },
    }


def get_top_reporters(queryset, limit=10):
    """
    Return the top reporters within the supplied barangay.
    """
    reports = get_analytics_reports(queryset)

    return list(
        reports
        .values("user__username")
        .annotate(total=Count("id"))
        .order_by("-total")[:limit]
    )


def get_report_trend(
    queryset,
    period="all_time",
    start_date=None,
    end_date=None,
):
    """
    Return report counts grouped by an appropriate time interval.

    Supported periods:
    - all_time
    - past_year
    - past_month
    - this_week
    - today
    - date_range

    Custom date ranges require start_date and end_date.
    """
    reports = get_analytics_reports(queryset)

    today = timezone.localdate()

    if period == "today":
        start_date = today
        end_date = today

    elif period == "this_week":
        start_date = today - timedelta(days=today.weekday())
        end_date = today

    elif period == "past_month":
        start_date = today - timedelta(days=29)
        end_date = today

    elif period == "past_year":
        try:
            start_date = today.replace(year=today.year - 1)
        except ValueError:
            # Handles February 29 when the previous year is not a leap year.
            start_date = today.replace(
                year=today.year - 1,
                day=28,
            )

        end_date = today

    elif period == "all_time":
        earliest = reports.aggregate(
            earliest=Min("created_at")
        )["earliest"]

        if earliest is None:
            return {
                "period": period,
                "interval": "month",
                "data": [],
            }

        start_date = timezone.localtime(earliest).date()
        end_date = today

    elif period == "date_range":
        if not start_date or not end_date:
            raise ValueError(
                "Both start_date and end_date are required "
                "for a custom date range."
            )

        if start_date > end_date:
            raise ValueError(
                "start_date cannot be later than end_date."
            )

        if end_date > today:
            raise ValueError(
                "end_date cannot be in the future."
            )

    else:
        raise ValueError("Invalid report trend period.")

    if start_date > end_date:
        raise ValueError(
            "The selected date range is invalid."
        )

    start_datetime = timezone.make_aware(
        datetime.combine(start_date, time.min)
    )

    end_datetime = timezone.make_aware(
        datetime.combine(
            end_date + timedelta(days=1),
            time.min,
        )
    )

    reports = reports.filter(
        created_at__gte=start_datetime,
        created_at__lt=end_datetime,
    )

    number_of_days = (end_date - start_date).days

    # Select an interval appropriate for the selected date range.
    if period == "today":
        interval = "hour"
    elif period in ("this_week", "past_month"):
        interval = "day"
    elif period == "past_year":
        interval = "month"
    elif number_of_days <= 2:
        interval = "hour"
    elif number_of_days <= 62:
        interval = "day"
    elif number_of_days <= 730:
        interval = "month"
    elif number_of_days <= 1825:
        interval = "month"
    else:
        interval = "year"

    truncation_functions = {
        "hour": TruncHour,
        "day": TruncDate,
        "month": TruncMonth,
        "year": TruncYear,
    }

    truncation = truncation_functions[interval]

    results = (
        reports
        .annotate(date_group=truncation("created_at"))
        .values("date_group")
        .annotate(total=Count("id"))
        .order_by("date_group")
    )

    data = []

    for item in results:
        date_group = item["date_group"]

        if interval == "hour":
            label = timezone.localtime(date_group).strftime(
                "%Y-%m-%dT%H:00"
            )
        elif interval == "day":
            label = date_group.isoformat()
        elif interval == "month":
            label = date_group.strftime("%Y-%m")
        else:
            label = str(date_group.year)

        data.append({
            "date": label,
            "total": item["total"],
        })

    return {
        "period": period,
        "interval": interval,
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "data": data,
    }


def get_emergency_categories(queryset):
    """
    Return report counts for every defined emergency category,
    including categories with zero reports.
    """
    reports = get_analytics_reports(queryset)

    results = (
        reports
        .values("category")
        .annotate(total=Count("id"))
    )

    counts = {
        item["category"]: item["total"]
        for item in results
    }

    return [
        {
            "category": value,
            "label": label,
            "total": counts.get(value, 0),
        }
        for value, label in Category.choices
    ]


def get_peak_incident_hours(queryset):
    """
    Group reports by the time of submission:
    Morning:   06:00 - 11:59
    Afternoon: 12:00 - 17:59
    Night:     18:00 - 05:59
    """
    reports = get_analytics_reports(queryset)

    hourly_results = (
        reports
        .annotate(hour=ExtractHour("created_at"))
        .values("hour")
        .annotate(total=Count("id"))
    )

    counts = {
        "morning": 0,
        "afternoon": 0,
        "night": 0,
    }

    for item in hourly_results:
        hour = item["hour"]
        total = item["total"]

        if 6 <= hour < 12:
            counts["morning"] += total
        elif 12 <= hour < 18:
            counts["afternoon"] += total
        else:
            counts["night"] += total

    return counts



def get_dbscan_clusters(
    queryset,
    eps_km=0.2,
    min_samples=3,
):
    """
    Generate geographic clusters from eligible reports.

    Noise reports receive cluster = -1.

    Returns:
        - Summary of detected clusters
        - Number of reports per cluster
        - Individual report cluster assignments
    """
    reports = (
        get_analytics_reports(queryset)
        .filter(
            latitude__isnull=False,
            longitude__isnull=False,
            latitude__gte=-90,
            latitude__lte=90,
            longitude__gte=-180,
            longitude__lte=180,
        )
        .values(
            "id",
            "latitude",
            "longitude",
        )
    )

    reports = list(reports)

    # Return a consistent response even when there
    # are not enough reports to perform clustering.
    if len(reports) < min_samples:
        return {
            "summary": {
                "total_clusters": 0,
                "total_clustered_reports": 0,
                "total_noise_reports": 0,
            },
            "clusters": [],
            "reports": [],
        }

    coords = np.array(
        [
            [
                float(report["latitude"]),
                float(report["longitude"]),
            ]
            for report in reports
        ],
        dtype=float,
    )

    earth_radius_km = 6371.0088
    epsilon = eps_km / earth_radius_km

    model = DBSCAN(
        eps=epsilon,
        min_samples=min_samples,
        algorithm="ball_tree",
        metric="haversine",
    )

    labels = model.fit_predict(
        np.radians(coords)
    )

    # Count reports belonging to each cluster.
    cluster_counts = {}

    for label in labels:
        if label == -1:
            continue

        cluster_counts[int(label)] = (
            cluster_counts.get(int(label), 0) + 1
        )

    # Prepare cluster summaries.
    clusters = [
        {
            "cluster": label,
            "total_reports": total,
        }
        for label, total in sorted(cluster_counts.items())
    ]

    # Prepare individual report assignments.
    report_assignments = [
        {
            "id": report["id"],
            "latitude": report["latitude"],
            "longitude": report["longitude"],
            "cluster": int(label),
        }
        for report, label in zip(reports, labels)
    ]

    total_clustered_reports = sum(cluster_counts.values())
    total_noise_reports = int(sum(labels == -1))

    return {
        "summary": {
            "total_clusters": len(cluster_counts),
            "total_clustered_reports": total_clustered_reports,
            "total_noise_reports": total_noise_reports,
        },
        "clusters": clusters,
        "reports": report_assignments,
    }
