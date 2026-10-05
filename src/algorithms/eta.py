"""
ETA (Estimated Time of Arrival) Prediction and absolute clock handling.

ETA is purely model-based, derived from `route.total_time`.
Absolute arrival deadline evaluation differs strictly from Phase 4 journey duration.
Core functions never use `datetime.now()` implicitly.
All datetimes MUST be timezone-aware.
"""
from datetime import datetime, timedelta
import math
from zoneinfo import ZoneInfo
from typing import TypedDict, List
from src.graph.models import Route

DHAKA_TIMEZONE = ZoneInfo("Asia/Dhaka")

class ETAResult(TypedDict):
    route: Route
    departure_time: datetime
    journey_duration_min: float
    estimated_arrival_time: datetime
    arrival_deadline: datetime | None
    on_time: bool | None
    minutes_early: float | None
    minutes_late: float | None

def _validate_datetime(dt: datetime | None, name: str) -> None:
    """Validates that a datetime object is not None and is timezone-aware."""
    if dt is None:
        raise ValueError(f"{name} cannot be None.")
    if not isinstance(dt, datetime):
        raise TypeError(f"{name} must be a datetime object.")
    if dt.tzinfo is None or dt.tzinfo.utcoffset(dt) is None:
        raise ValueError(f"{name} must be a timezone-aware datetime.")

def _validate_duration(duration: float) -> float:
    if isinstance(duration, bool):
        raise TypeError("Duration cannot be a boolean.")
    if not isinstance(duration, (int, float)):
        raise TypeError("Duration must be numeric.")
    if math.isnan(duration) or math.isinf(duration):
        raise ValueError("Duration must be finite.")
    if duration < 0:
        raise ValueError("Duration cannot be negative.")
    return float(duration)

def estimate_arrival_time(route: Route, departure_time: datetime) -> datetime:
    """
    Estimates arrival time purely based on route duration.
    """
    _validate_datetime(departure_time, "departure_time")
    duration = _validate_duration(route.total_time)
    
    return departure_time + timedelta(minutes=duration)

def check_arrival_deadline(
    route: Route,
    departure_time: datetime,
    arrival_deadline: datetime | None = None
) -> ETAResult:
    """
    Calculates ETA and evaluates absolute arrival deadline.
    Returns a structured dictionary with timing metadata.
    """
    _validate_datetime(departure_time, "departure_time")
    
    if arrival_deadline is not None:
        _validate_datetime(arrival_deadline, "arrival_deadline")
        
    duration = _validate_duration(route.total_time)
    estimated_arrival = departure_time + timedelta(minutes=duration)
    
    result: ETAResult = {
        "route": route,
        "departure_time": departure_time,
        "journey_duration_min": duration,
        "estimated_arrival_time": estimated_arrival,
        "arrival_deadline": arrival_deadline,
        "on_time": None,
        "minutes_early": None,
        "minutes_late": None
    }
    
    if arrival_deadline is not None:
        # absolute delta (arrival_deadline - estimated_arrival).total_seconds()
        diff_seconds = (arrival_deadline - estimated_arrival).total_seconds()
        
        # if arrival <= deadline, diff_seconds >= 0 -> on time
        if diff_seconds >= 0:
            result["on_time"] = True
            result["minutes_early"] = diff_seconds / 60.0
            result["minutes_late"] = 0.0
        else:
            result["on_time"] = False
            result["minutes_early"] = 0.0
            result["minutes_late"] = abs(diff_seconds) / 60.0
            
    return result

def evaluate_routes_for_deadline(
    routes: List[Route],
    departure_time: datetime,
    arrival_deadline: datetime | None = None
) -> List[ETAResult]:
    """
    Evaluates a list of routes against a departure time and optional absolute deadline.
    Returns the metadata for all routes (does not discard late routes).
    """
    return [check_arrival_deadline(r, departure_time, arrival_deadline) for r in routes]
