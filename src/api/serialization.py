"""
Helper module for JSON serialization of Journey Planner results.
"""
from datetime import datetime
from typing import Any, Dict, List

from src.graph.models import Route, Leg


def _serialize_leg(leg: Leg) -> Dict[str, Any]:
    return {
        "frm": leg.frm,
        "to": leg.to,
        "mode": leg.mode,
        "time": leg.time,
        "cost": leg.cost,
        "distance": leg.distance
    }


def _serialize_route(route: Route) -> Dict[str, Any]:
    return {
        "time_min": route.total_time,
        "cost_bdt": route.total_cost,
        "distance_km": route.total_distance,
        "transfers": route.num_transfers,
        "walk_km": route.walking_distance,
        "mode_sequence": route.mode_sequence,
        "legs": [_serialize_leg(leg) for leg in route.legs]
    }


def serialize_result(data: Any) -> Any:
    """
    Recursively traverse a dictionary or list, converting non-JSON serializable
    objects like datetimes and Route models into standard Python types.
    """
    if isinstance(data, dict):
        return {k: serialize_result(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [serialize_result(i) for i in data]
    elif isinstance(data, datetime):
        return data.isoformat()
    elif isinstance(data, Route):
        return _serialize_route(data)
    elif isinstance(data, Leg):
        return _serialize_leg(data)
    
    # Primitives and None safely pass through
    return data
