import math
# ----------------------------
# Haversine Distance Function
# ----------------------------
def haversine(lat1, lon1, lat2, lon2):
    R = 6371  # Earth radius in km

    # convert degrees → radians
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)

    # haversine formula
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return R * c


# ----------------------------
# Find Nearest Location
# ----------------------------
def find_nearest(accident_location, locations):
    accident_lat, accident_lon = accident_location

    closest = None
    min_distance = float("inf")

    for r in locations:
        distance = haversine(
            accident_lat,
            accident_lon,
            r["latitude"],
            r["longitude"]
        )

        if distance < min_distance:
            min_distance = distance
            closest = r

    return closest, min_distance