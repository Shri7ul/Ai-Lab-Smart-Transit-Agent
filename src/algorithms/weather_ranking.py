import pandas as pd
from typing import List, Dict, Any, TypedDict
from src.graph.models import Route
from src.algorithms.multicriteria import rank_and_evaluate_routes

MAX_WEATHER_PENALTY = 0.20
WALK_EXPOSURE_REFERENCE_KM = 1.0
TRANSFER_EXPOSURE_REFERENCE = 3.0

class WeatherRankResult(TypedDict):
    route: Route
    route_id: str
    base_score: float
    weather_severity: float
    walking_exposure: float
    transfer_exposure: float
    weather_penalty: float
    adjusted_score: float
    weather_reason: str

def assess_weather_severity(weather: Dict[str, Any]) -> float:
    """
    Project-level heuristic to determine weather severity (0.0 to 1.0).
    Not an official meteorological standard.
    """
    if not isinstance(weather, dict):
        raise TypeError("Weather data must be a dictionary.")
        
    condition = weather.get("condition")
    if not isinstance(condition, str):
        raise TypeError("Weather condition must be a string.")
        
    rain_mm = float(weather.get("rain_1h_mm", 0.0))
    snow_mm = float(weather.get("snow_1h_mm", 0.0))
    wind_mps = float(weather.get("wind_speed_mps", 0.0))
    visibility_m = weather.get("visibility_m")
    
    if rain_mm < 0 or snow_mm < 0 or wind_mps < 0:
        raise ValueError("Weather metrics cannot be negative.")
    if visibility_m is not None and float(visibility_m) < 0:
        raise ValueError("Visibility cannot be negative.")
        
    severity = 0.0
    
    cond_lower = condition.lower()
    
    # Base condition severity
    if cond_lower in ("clear", "clouds"):
        severity = 0.0
    elif cond_lower in ("drizzle", "mist", "haze", "fog"):
        severity = 0.25
    elif cond_lower == "rain":
        severity = 0.40
    elif cond_lower == "snow":
        severity = 0.50
    elif cond_lower == "thunderstorm":
        severity = 0.75
    else:
        # Unknown adverse condition fallback
        severity = 0.20
        
    # Additive adjustments
    if rain_mm > 0.0:
        if rain_mm > 5.0:
            severity += 0.30  # Heavy rain
        else:
            severity += 0.15  # Light/moderate rain
            
    if snow_mm > 0.0:
        severity += 0.20
        
    if wind_mps > 10.0:
        severity += 0.15
        
    if visibility_m is not None and visibility_m < 1000:
        severity += 0.15
        
    return min(1.0, max(0.0, severity))

def _determine_weather_reason(severity: float, condition: str, rain_mm: float, snow_mm: float) -> str:
    if severity == 0.0:
        return "no_adverse_weather"
        
    cond_lower = condition.lower()
    
    if cond_lower == "thunderstorm":
        return "thunderstorm_outdoor_exposure"
    elif snow_mm > 0 or cond_lower == "snow":
        return "snow_outdoor_exposure"
    elif rain_mm > 0 or cond_lower in ("rain", "drizzle"):
        return "rain_walking_exposure"
    elif cond_lower in ("mist", "fog", "haze") or severity > 0.0:
        return "adverse_visibility_or_wind_exposure"
        
    return "general_adverse_weather"

def calculate_weather_penalty(route: Route, weather_severity: float) -> tuple[float, float, float]:
    """
    Calculates the weather penalty for a given route.
    Walking distance is weighted more heavily than transfers.
    Returns: (weather_penalty, walking_exposure, transfer_exposure)
    """
    # Calculate exposures bounded 0 to 1
    walk_dist = route.walking_distance
    transfers = route.num_transfers
    
    walk_exposure = min(walk_dist / WALK_EXPOSURE_REFERENCE_KM, 1.0)
    transfer_exposure = min(transfers / TRANSFER_EXPOSURE_REFERENCE, 1.0)
    
    # Combine exposures (walking is weighted more)
    exposure_factor = 0.75 * walk_exposure + 0.25 * transfer_exposure
    
    penalty = weather_severity * exposure_factor * MAX_WEATHER_PENALTY
    
    # Clamp penalty
    penalty = min(MAX_WEATHER_PENALTY, max(0.0, penalty))
    
    return penalty, walk_exposure, transfer_exposure

def rank_routes_with_weather(routes: List[Route], weather: Dict[str, Any], weights: dict[str, float] | None = None) -> list[WeatherRankResult]:
    """
    Applies the secondary weather ranking layer to candidate routes.
    
    Returns a list of dicts, sorted by adjusted_score descending.
    """
    if weather is None:
        raise TypeError("Weather data cannot be None.")
        
    if not routes:
        return []
        
    # 1. Obtain baseline multicriteria scores
    if weights is None:
        base_df = rank_and_evaluate_routes(routes)
    else:
        base_df = rank_and_evaluate_routes(routes, weights=weights)
    
    # 2. Determine project-level weather severity
    severity = assess_weather_severity(weather)
    
    rain_mm = float(weather.get("rain_1h_mm", 0.0))
    snow_mm = float(weather.get("snow_1h_mm", 0.0))
    reason = _determine_weather_reason(severity, weather.get("condition", ""), rain_mm, snow_mm)
    
    results: list[WeatherRankResult] = []
    
    # Match strings like "R1" back to routes[0]
    # base_df has a "route" column
    for _, row in base_df.iterrows():
        route_id_str = row["route"]  # "R1", "R2", ...
        idx = int(route_id_str[1:]) - 1
        route_obj = routes[idx]
        base_score = float(row["score"])
        
        penalty, walk_exp, transfer_exp = calculate_weather_penalty(route_obj, severity)
        
        adjusted_score = max(0.0, base_score - penalty)
        
        results.append({
            "route": route_obj,
            "route_id": route_id_str,
            "base_score": base_score,
            "weather_severity": severity,
            "walking_exposure": walk_exp,
            "transfer_exposure": transfer_exp,
            "weather_penalty": penalty,
            "adjusted_score": adjusted_score,
            "weather_reason": reason
        })
        
    # 3. Re-sort by adjusted_score descending
    # In case of ties, Python's Timsort is stable, so original base ranking order is preserved
    results.sort(key=lambda x: x["adjusted_score"], reverse=True)
    
    return results
