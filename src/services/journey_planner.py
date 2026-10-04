"""
Journey Planner Pipeline orchestration module (Phase 11).
"""
import copy
from datetime import datetime
import time
from typing import Dict, Any, List, Optional, TypedDict

from src.api.gemini_query import parse_travel_query, TravelQueryResult
from src.api.geocoding import geocode_place, GeocodingError
from src.api.weather import get_current_weather, WeatherError

from src.graph.graph_builder import get_default_graph
from src.graph.access import find_nearest_stops, add_temporary_connectors
from src.graph.models import Route

from src.algorithms.k_shortest import k_shortest_routes
from src.algorithms.constraints import filter_routes_by_constraints
from src.algorithms.multicriteria import rank_and_evaluate_routes, DEFAULT_WEIGHTS
from src.algorithms.weather_ranking import rank_routes_with_weather, WeatherRankResult
from src.algorithms.eta import check_arrival_deadline, evaluate_routes_for_deadline, ETAResult


class JourneyPlanningError(Exception):
    """Application-level exception for pipeline failures."""
    pass


PREFERENCE_WEIGHTS = {
    "balanced": {"time": 0.45, "cost": 0.20, "transfers": 0.20, "walking": 0.15},
    "fastest": {"time": 0.70, "cost": 0.10, "transfers": 0.10, "walking": 0.10},
    "cheapest": {"time": 0.20, "cost": 0.60, "transfers": 0.10, "walking": 0.10},
    "less_walking": {"time": 0.25, "cost": 0.15, "transfers": 0.10, "walking": 0.50},
    "fewer_transfers": {"time": 0.25, "cost": 0.15, "transfers": 0.50, "walking": 0.10}
}


def _get_weights_for_multiple_preferences(prefs: List[Any]) -> Dict[str, float]:
    pref_map = {
        "fastest": "time",
        "lowest_cost": "cost",
        "cheapest": "cost",
        "less_walking": "walking",
        "fewer_transfers": "transfers",
        "balanced": None
    }
    
    metrics = ["time", "cost", "walking", "transfers"]
    
    if not prefs:
        return DEFAULT_WEIGHTS
        
    unique_prefs: list[str] = []
    
    for pref in prefs:
        metric = pref_map.get(pref)
        
        if metric is None:
            continue
            
        if metric not in metrics:
            continue
            
        if metric not in unique_prefs:
            unique_prefs.append(metric)
            
    if not unique_prefs or "balanced" in prefs:
        return DEFAULT_WEIGHTS
        
    n = len(unique_prefs)
    weights = {m: 0.05 for m in metrics}
    
    if n == 1:
        weights[unique_prefs[0]] += 0.80
    elif n == 2:
        weights[unique_prefs[0]] += 0.45
        weights[unique_prefs[1]] += 0.35
    elif n == 3:
        weights[unique_prefs[0]] += 0.40
        weights[unique_prefs[1]] += 0.25
        weights[unique_prefs[2]] += 0.15
    elif n >= 4:
        weights[unique_prefs[0]] += 0.35
        weights[unique_prefs[1]] += 0.25
        weights[unique_prefs[2]] += 0.15
        weights[unique_prefs[3]] += 0.05
        
    total = sum(weights.values())
    return {k: v / total for k, v in weights.items()}


def _build_map_data(route: Route, origin_geo: Dict, dest_geo: Dict, origin_str: str, dest_str: str, stops_df: Any) -> Dict:
    def get_node_coords(node_id: str):
        if node_id == "__USER_ORIGIN__":
            return float(origin_geo["latitude"]), float(origin_geo["longitude"]), origin_str
        if node_id == "__USER_DESTINATION__":
            return float(dest_geo["latitude"]), float(dest_geo["longitude"]), dest_str
        
        stop_row = stops_df[stops_df['stop_id'] == node_id]
        if not stop_row.empty:
            return float(stop_row.iloc[0]['lat']), float(stop_row.iloc[0]['lon']), str(stop_row.iloc[0]['stop_name'])
        return None, None, node_id

    map_data = {
        "origin": {"lat": float(origin_geo["latitude"]), "lon": float(origin_geo["longitude"]), "name": origin_str},
        "destination": {"lat": float(dest_geo["latitude"]), "lon": float(dest_geo["longitude"]), "name": dest_str},
        "legs": []
    }

    for leg in route.legs:
        frm_lat, frm_lon, frm_name = get_node_coords(leg.frm)
        to_lat, to_lon, to_name = get_node_coords(leg.to)
        
        if frm_lat is not None and to_lat is not None:
            map_data["legs"].append({
                "mode": leg.mode,
                "frm": {"lat": frm_lat, "lon": frm_lon, "name": frm_name, "id": leg.frm},
                "to": {"lat": to_lat, "lon": to_lon, "name": to_name, "id": leg.to}
            })
            
    return map_data


def plan_journey(
    user_query: str,
    departure_time: Optional[datetime] = None,
    arrival_deadline: Optional[datetime] = None,
    candidate_count: int = 5,
    verbose: bool = False
) -> Dict[str, Any]:
    """
    Executes the full transit planning pipeline.
    """
    if not isinstance(candidate_count, int) or isinstance(candidate_count, bool) or candidate_count < 1:
        raise ValueError("candidate_count must be an integer >= 1.")

    if verbose: print("[1/7] Parsing query with Gemini...")
    t_start = time.perf_counter()
    # 1. Query Understanding
    try:
        query_result: TravelQueryResult = parse_travel_query(user_query)
    except RuntimeError as exc:
        raise JourneyPlanningError(f"[query_understanding] {exc}") from exc
    except Exception as e:
        raise JourneyPlanningError(f"[query_understanding] {str(e)}") from e

    # Merge UI and NLP time (UI overrides NLP)
    nlp_dep_str = query_result.get("departure_time")
    nlp_arr_str = query_result.get("arrival_deadline")
    
    if departure_time is None and nlp_dep_str:
        try:
            dt = datetime.fromisoformat(nlp_dep_str)
            if dt.tzinfo is not None:
                departure_time = dt
        except ValueError:
            pass

    if arrival_deadline is None and nlp_arr_str:
        try:
            dt = datetime.fromisoformat(nlp_arr_str)
            if dt.tzinfo is not None:
                arrival_deadline = dt
        except ValueError:
            pass

    if arrival_deadline is not None and departure_time is None:
        from zoneinfo import ZoneInfo
        dhaka_tz = ZoneInfo("Asia/Dhaka")
        now_dhaka = datetime.now(dhaka_tz)
        if arrival_deadline < now_dhaka:
            raise JourneyPlanningError("[eta] Arrival deadline has already passed. Please clarify the intended date and time.")
        departure_time = now_dhaka

    origin_str = query_result.get("origin")
    dest_str = query_result.get("destination")
    
    if not origin_str:
        raise JourneyPlanningError("[query_understanding] Origin is missing from the query.")
    if not dest_str:
        raise JourneyPlanningError("[query_understanding] Destination is missing from the query.")

    if verbose: print("[2/7] Geocoding origin...")
    t_gemini = time.perf_counter()
    # 2. Geocoding
    try:
        origin_geo = geocode_place(origin_str)
        t_origin = time.perf_counter()
        if not origin_geo:
            raise JourneyPlanningError(f"[geocoding] Origin location '{origin_str}' could not be resolved.")
            
        if verbose: print("[3/7] Geocoding destination...")
        dest_geo = geocode_place(dest_str)
        if not dest_geo:
            raise JourneyPlanningError(f"[geocoding] Destination location '{dest_str}' could not be resolved.")
    except GeocodingError as e:
        raise JourneyPlanningError(f"[geocoding] Failed to resolve locations: {str(e)}") from e

    if verbose: print("[4/7] Finding transit access...")
    t_dest = time.perf_counter()
    # 3. Transit Access
    base_graph, stops_df = get_default_graph()
    
    origin_stops = find_nearest_stops(origin_geo["latitude"], origin_geo["longitude"], stops_df, limit=3)
    if not origin_stops:
        raise JourneyPlanningError("[transit_access] No transit stop found near the origin.")
        
    dest_stops = find_nearest_stops(dest_geo["latitude"], dest_geo["longitude"], stops_df, limit=3)
    if not dest_stops:
        raise JourneyPlanningError("[transit_access] No transit stop found near the destination.")

    if verbose: print("[5/7] Generating/filtering/ranking routes...")
    # 4. Routing
    G_work = add_temporary_connectors(
        base_graph, "__USER_ORIGIN__", origin_geo["latitude"], origin_geo["longitude"], origin_stops, "origin"
    )
    G_work = add_temporary_connectors(
        G_work, "__USER_DESTINATION__", dest_geo["latitude"], dest_geo["longitude"], dest_stops, "destination"
    )
    t_access = time.perf_counter()

    try:
        raw_routes = k_shortest_routes(G_work, "__USER_ORIGIN__", "__USER_DESTINATION__", k=candidate_count)
    except Exception as e:
        raise JourneyPlanningError(f"[routing] Engine failure: {str(e)}") from e
    t_routing = time.perf_counter()

    if not raw_routes:
        raise JourneyPlanningError("[routing] No transit route could be found.")

    # 5. Constraints
    budget = query_result.get("budget")
    max_time = query_result.get("deadline_minutes")
    
    constraint_result = filter_routes_by_constraints(raw_routes, budget=budget, max_time=max_time)
    feasible_routes = constraint_result["feasible"]
    rejected_routes_info = constraint_result["rejected"]
    
    if not feasible_routes:
        budget_failed = all("budget_exceeded" in r["reasons"] for r in rejected_routes_info)
        time_failed = all("time_exceeded" in r["reasons"] for r in rejected_routes_info)
        if budget_failed and not time_failed:
            raise JourneyPlanningError("[constraints] No route can satisfy the selected budget.")
        elif time_failed and not budget_failed:
            raise JourneyPlanningError("[constraints] No route can satisfy the selected duration.")
        else:
            raise JourneyPlanningError("[constraints] No route can satisfy the selected journey constraints.")

    # 5.5 Arrival Deadline Hard Filter
    late_routes = []
    feasible_on_time = []
    for r_obj in feasible_routes:
        if departure_time is not None and arrival_deadline is not None:
            eta_res = check_arrival_deadline(r_obj, departure_time, arrival_deadline)
            if eta_res["on_time"] is False:
                late_routes.append(r_obj)
            else:
                feasible_on_time.append(r_obj)
        else:
            feasible_on_time.append(r_obj)
            
    if not feasible_on_time:
        raise JourneyPlanningError("[constraints] No route can satisfy the selected arrival deadline.")
        
    feasible_routes = feasible_on_time
    t_constraints = time.perf_counter()

    # 6. User Preference Mapping
    prefs = query_result.get("preferences", [])
    # If budget was mentioned, it acts as a soft preference for lowest cost too
    if query_result.get("budget") is not None and "lowest_cost" not in prefs:
        prefs.append("lowest_cost")
        
    weights = _get_weights_for_multiple_preferences(prefs)
    t_prefs = time.perf_counter()

    if verbose: print("[6/7] Fetching weather...")
    # 7. Weather Location & Weather-Aware Ranking
    weather_available = False
    weather_data = None
    weather_warning = None
    
    try:
        weather_data = get_current_weather(origin_geo["latitude"], origin_geo["longitude"])
        weather_available = True
    except WeatherError as e:
        weather_warning = "Weather fetch failed. Defaulting to base ranking."
    except Exception as e:
        weather_warning = "Unexpected error fetching weather. Defaulting to base ranking."

    ranked_routes: List[Dict[str, Any]] = []

    if weather_available and weather_data:
        weather_results = rank_routes_with_weather(feasible_routes, weather_data, weights=weights)
        for i, w_res in enumerate(weather_results, start=1):
            ranked_routes.append({
                "rank": i,
                "route": w_res["route"],
                "base_score": w_res["base_score"],
                "weather_penalty": w_res["weather_penalty"],
                "adjusted_score": w_res["adjusted_score"]
            })
    else:
        base_df = rank_and_evaluate_routes(feasible_routes, weights=weights)
        for i, row in base_df.iterrows():
            idx = int(str(row["route"])[1:]) - 1
            r_obj = feasible_routes[idx]
            ranked_routes.append({
                "rank": int(float(str(row["rank"]))),
                "route": r_obj,
                "base_score": float(str(row["score"])),
                "weather_penalty": 0.0,
                "adjusted_score": float(str(row["score"]))
            })
    t_weather = time.perf_counter()

    if verbose: print("[7/7] Building final recommendations...")
    # 8. ETA & Absolute Deadline Evaluation
    final_recommendations = []

    for r_dict in ranked_routes:
        r_obj = r_dict["route"]
        
        eta_metadata: Dict[str, Any] = {
            "departure_time": None,
            "estimated_arrival_time": None,
            "arrival_deadline": None,
            "on_time": None,
            "minutes_early": None,
            "minutes_late": None
        }

        if departure_time is not None:
            eta_res = check_arrival_deadline(r_obj, departure_time, arrival_deadline)
            eta_metadata.update(eta_res)

        rec = {
            "rank": 0, # Will be re-assigned after sorting
            "mode_sequence": " -> ".join(r_obj.mode_sequence),
            "time_min": r_obj.total_time,
            "cost_bdt": r_obj.total_cost,
            "transfers": r_obj.num_transfers,
            "walk_km": round(r_obj.walking_distance, 2),
            "base_score": r_dict["base_score"],
            "weather_penalty": r_dict["weather_penalty"],
            "adjusted_score": r_dict["adjusted_score"],
            "map": _build_map_data(r_obj, origin_geo, dest_geo, origin_str, dest_str, stops_df),
            **eta_metadata
        }

        final_recommendations.append(rec)

    # 9. Final Sorting Policy
    # Sort by adjusted_score desc, base_score desc.
    # Python's list.sort is stable.
    final_recommendations.sort(key=lambda x: (x["adjusted_score"], x["base_score"]), reverse=True)

    # Re-assign ranks sequentially
    for idx, rec in enumerate(final_recommendations, start=1):
        rec["rank"] = idx

    # Build late_recommendations separately for backend metadata without ranking
    late_recommendations = []
    for r_obj in late_routes:
        eta_metadata: Dict[str, Any] = {
            "departure_time": None,
            "estimated_arrival_time": None,
            "arrival_deadline": None,
            "on_time": None,
            "minutes_early": None,
            "minutes_late": None
        }
        if departure_time is not None:
            eta_res = check_arrival_deadline(r_obj, departure_time, arrival_deadline)
            eta_metadata.update(eta_res)
            
        late_recommendations.append({
            "rank": 0,
            "mode_sequence": " -> ".join(r_obj.mode_sequence),
            "time_min": r_obj.total_time,
            "cost_bdt": r_obj.total_cost,
            "transfers": r_obj.num_transfers,
            "walk_km": round(r_obj.walking_distance, 2),
            "base_score": 0.0,
            "weather_penalty": 0.0,
            "adjusted_score": 0.0,
            "map": _build_map_data(r_obj, origin_geo, dest_geo, origin_str, dest_str, stops_df),
            **eta_metadata
        })

    # Format rejected routes cleanly without exposing raw objects
    clean_rejected = []
    for rej in rejected_routes_info:
        r = rej["route"]
        clean_rejected.append({
            "mode_sequence": " -> ".join(r.mode_sequence),
            "time_min": r.total_time,
            "cost_bdt": r.total_cost,
            "reasons": rej["reasons"]
        })
    t_serialization = time.perf_counter()
    
    # Optional performance printing
    if verbose:
        print(f"[PERF] Gemini: {t_gemini - t_start:.2f}s")
        print(f"[PERF] Origin geocode: {t_origin - t_gemini:.2f}s")
        print(f"[PERF] Destination geocode: {t_dest - t_origin:.2f}s")
        print(f"[PERF] Transit access: {t_access - t_dest:.2f}s")
        print(f"[PERF] Routing: {t_routing - t_access:.2f}s")
        print(f"[PERF] Constraints: {t_constraints - t_routing:.2f}s")
        print(f"[PERF] Ranking (prefs): {t_prefs - t_constraints:.2f}s")
        print(f"[PERF] Weather & Weather Ranking: {t_weather - t_prefs:.2f}s")
        print(f"[PERF] Serialization: {t_serialization - t_weather:.2f}s")
        print(f"[PERF] Total: {t_serialization - t_start:.2f}s")

    # 10. Assemble Final Result
    result = {
        "query": {
            "raw": user_query,
            "origin": origin_str,
            "destination": dest_str,
            "budget": budget,
            "max_journey_minutes": max_time,
            "preference": query_result.get("preference")
        },
        "origin": {
            "geocoding": origin_geo,
            "access_stops": origin_stops
        },
        "destination": {
            "geocoding": dest_geo,
            "access_stops": dest_stops
        },
        "weather": weather_data,
        "weather_available": weather_available,
        "weather_warning": weather_warning,
        "candidate_count": len(raw_routes),
        "feasible_count": len(final_recommendations),
        "rejected_count": len(clean_rejected),
        "recommendations": final_recommendations,
        "rejected_routes": clean_rejected,
        "late_routes": late_recommendations
    }

    return result
