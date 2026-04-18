"""
Geofencing utilities.
All geofence checks happen SERVER-SIDE — client-reported location is
validated here, not trusted blindly.

Anti-spoofing note:
  GPS can be spoofed by rooted devices. This layer works in combination
  with the face + liveness layers. No single layer is relied upon alone.
"""

import math
from dataclasses import dataclass


@dataclass
class GeoPoint:
    latitude: float
    longitude: float


def haversine_distance(point1: GeoPoint, point2: GeoPoint) -> float:
    """
    Calculate the great-circle distance between two GPS coordinates in metres.
    Uses the Haversine formula.
    """
    R = 6_371_000  # Earth radius in metres

    lat1 = math.radians(point1.latitude)
    lat2 = math.radians(point2.latitude)
    dlat = math.radians(point2.latitude - point1.latitude)
    dlon = math.radians(point2.longitude - point1.longitude)

    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


def is_within_radius(
    student_location: GeoPoint,
    classroom_location: GeoPoint,
    radius_meters: float,
    gps_error_buffer_meters: float = 50.0,
) -> tuple[bool, float]:
    """
    Check if a student is within the classroom geofence.

    Args:
        student_location: GPS coordinates reported by student's browser
        classroom_location: GPS coordinates set by teacher
        radius_meters: Classroom radius in metres (set by teacher)
        gps_error_buffer_meters: Added buffer for GPS accuracy variance (default 50m for indoor browser GPS)

    Returns:
        (is_inside: bool, distance_meters: float)
    """
    distance = haversine_distance(student_location, classroom_location)
    effective_radius = radius_meters + gps_error_buffer_meters
    return distance <= effective_radius, round(distance, 2)


def validate_location_data(lat: float, lon: float) -> bool:
    """Sanity-check that reported coordinates are geographically valid."""
    return -90 <= lat <= 90 and -180 <= lon <= 180
