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


def find_candidate_reports(report): #report = newly created report
    cutoff = report.created_at - MAX_TIME_DIFFERENCE #If 10 am, cutoff = 9:50

    candidates = Report.objects.filter(
        barangay=report.barangay, #candidates = same barangay, 
        created_at__gte=cutoff, #candidates = created since the cutoff (9:50 onwards)
        created_at__lte=report.created_at, #candidates = created before or upon the report's time (10 am and before)
    ).exclude(
        id=report.id #candidates cannot include the current report being checked
    )

    nearby_candidates = []

    for candidate in candidates: #comaparing the geographical distance of the report and the candidates (Loop)
        distance = haversine(
            float(report.latitude),
            float(report.longitude),
            float(candidate.latitude),
            float(candidate.longitude),
        )

        if distance <= MAX_DISTANCE_KM: #if report and candidate's distance is lte 300 meters, then True
            time_difference = report.created_at - candidate.created_at #candidate(9:50), report (9:55) = 5 minutes

            nearby_candidates.append({
                "report": candidate, #refers to the report that came before (potentially original)
                "distance": distance,
                "time_difference": time_difference,
            })

    return nearby_candidates #return to the caller of the function


def calculate_candidate_similarity(report, candidate): #we compare txt similarity between new report and older report
    return jaccard_similarity( #proceeses the texts, then divide common words to unique words
        report.description,
        candidate.description,
    ) #if 3 words in common, but only 2 words unique, this returns 1.5


def calculate_distance_score(distance_km):
    if distance_km >= MAX_DISTANCE_KM:  #score becomes 0 if their distance is greater than the maximum coverage
        return 0.0

    return 1 - (distance_km / MAX_DISTANCE_KM) #if distance_km is 0.2, then this will return 0.33


def calculate_time_score(time_difference):
    if time_difference >= MAX_TIME_DIFFERENCE: #0 if time difference is greater than 10 minutes
        return 0.0

    return 1 - ( #if time diff is 3 minutes, this returns 0.3
        time_difference.total_seconds() #time between new report and older report 
        / MAX_TIME_DIFFERENCE.total_seconds() #10 minutes
    )


def calculate_overall_score(
    distance_score,
    time_score,
    jaccard_score,
):
    return (
        distance_score * DISTANCE_WEIGHT #0.33 * 0.40 = 0.132
        + time_score * TIME_WEIGHT #0.3 * 0.35 = 0.105
        + jaccard_score * JACCARD_WEIGHT #1.5 * 0.25 = 0.375
    ) # total = 0.61, threshold is 0.70


def is_potential_duplicate(overall_score):
    return overall_score >= POTENTIAL_DUPLICATE_THRESHOLD #0.61 = NOT potential duplicate


def detect_potential_duplicates(report): #report = newly created report
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
                "report": candidate, #the older report
                "distance": distance,
                "time_difference": time_difference,
                "distance_score": distance_score,
                "time_score": time_score,
                "jaccard_score": jaccard_score,
                "overall_score": overall_score,
            })

    return potential_duplicates #can be multiple since it's list and is looping

def save_potential_duplicates(report): #the newly created report
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