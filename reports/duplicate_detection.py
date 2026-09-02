from datetime import timedelta

from .models import Report, PotentialDuplicate
from .text_similarity import jaccard_similarity
from core.geo import haversine


MAX_TIME_DIFFERENCE = timedelta(minutes=10)
MAX_DISTANCE_KM = 0.3

DISTANCE_WEIGHT = 0.40
TIME_WEIGHT = 0.35
JACCARD_WEIGHT = 0.25

POTENTIAL_DUPLICATE_THRESHOLD = 0.70


def find_candidate_reports(report):
    cutoff = report.created_at - MAX_TIME_DIFFERENCE

    candidates = Report.objects.filter(
        barangay=report.barangay,
        created_at__gte=cutoff,
        created_at__lte=report.created_at,
    ).exclude(
        id=report.id
    )

    nearby_candidates = []

    for candidate in candidates:
        distance = haversine(
            float(report.latitude),
            float(report.longitude),
            float(candidate.latitude),
            float(candidate.longitude),
        )

        if distance <= MAX_DISTANCE_KM:
            time_difference = report.created_at - candidate.created_at

            nearby_candidates.append({
                "report": candidate,
                "distance": distance,
                "time_difference": time_difference,
            })

    return nearby_candidates


def calculate_candidate_similarity(report, candidate):
    return jaccard_similarity(
        report.description,
        candidate.description,
    )


def calculate_distance_score(distance_km):
    if distance_km >= MAX_DISTANCE_KM:
        return 0.0

    return 1 - (distance_km / MAX_DISTANCE_KM)


def calculate_time_score(time_difference):
    if time_difference >= MAX_TIME_DIFFERENCE:
        return 0.0

    return 1 - (
        time_difference.total_seconds()
        / MAX_TIME_DIFFERENCE.total_seconds()
    )


def calculate_overall_score(
    distance_score,
    time_score,
    jaccard_score,
):
    return (
        distance_score * DISTANCE_WEIGHT
        + time_score * TIME_WEIGHT
        + jaccard_score * JACCARD_WEIGHT
    )


def is_potential_duplicate(overall_score):
    return overall_score >= POTENTIAL_DUPLICATE_THRESHOLD


def detect_potential_duplicates(report):
    candidates = find_candidate_reports(report)

    potential_duplicates = []

    for candidate_data in candidates:
        candidate = candidate_data["report"]
        distance = candidate_data["distance"]
        time_difference = candidate_data["time_difference"]

        distance_score = calculate_distance_score(distance)

        time_score = calculate_time_score(
            time_difference
        )

        jaccard_score = calculate_candidate_similarity(
            report,
            candidate,
        )

        overall_score = calculate_overall_score(
            distance_score,
            time_score,
            jaccard_score,
        )

        if is_potential_duplicate(overall_score):
            potential_duplicates.append({
                "report": candidate,
                "distance": distance,
                "time_difference": time_difference,
                "distance_score": distance_score,
                "time_score": time_score,
                "jaccard_score": jaccard_score,
                "overall_score": overall_score,
            })

    return potential_duplicates

def save_potential_duplicates(report):
    results = detect_potential_duplicates(report)

    for result in results:
        PotentialDuplicate.objects.get_or_create(
            report=report,
            potential_duplicate=result["report"],
            defaults={
                "distance_meters": result["distance"] * 1000,
                "time_difference_seconds": (
                    result["time_difference"].total_seconds()
                ),
                "barangay_match": (
                    report.barangay == result["report"].barangay
                ),
                "description_similarity": result["jaccard_score"],
                "similarity_score": result["overall_score"],
            },
        )

    return results