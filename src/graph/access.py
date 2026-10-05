import pandas as pd
import networkx as nx
from typing import List, Dict, Any, Optional
import math
from src.utils.distance import haversine_km

WALK_SPEED_KMH = 4.5
DEFAULT_MAX_ACCESS_RADIUS_KM = 1.5

def find_nearest_stops(
    latitude: float,
    longitude: float,
    stops: pd.DataFrame,
    limit: int = 3,
    max_distance_km: Optional[float] = DEFAULT_MAX_ACCESS_RADIUS_KM,
) -> List[Dict[str, Any]]:
    """
    Finds the nearest transit stops to a given geographic coordinate.
    
    Args:
        latitude: float, user origin or destination latitude
        longitude: float, user origin or destination longitude
        stops: pd.DataFrame, standard transit stops dataframe containing stop_id, stop_name, lat, lon
        limit: int, maximum number of stops to return
        max_distance_km: float, maximum walking access radius in kilometers
        
    Returns:
        A list of dictionaries representing the nearest stops, sorted by distance ascending.
    """
    if latitude is None or longitude is None:
        raise TypeError("Coordinates cannot be None.")
    
    if not isinstance(latitude, (int, float)) or not isinstance(longitude, (int, float)):
        raise TypeError("Coordinates must be numeric.")
        
    if math.isnan(latitude) or math.isnan(longitude) or math.isinf(latitude) or math.isinf(longitude):
        raise ValueError("Coordinates cannot be NaN or infinite.")
        
    if not (-90.0 <= latitude <= 90.0) or not (-180.0 <= longitude <= 180.0):
        raise ValueError("Coordinates are out of standard geographic bounds.")
        
    if not isinstance(limit, int) or limit < 1:
        raise ValueError("Limit must be a positive integer.")
        
    if max_distance_km is not None and (not isinstance(max_distance_km, (int, float)) or max_distance_km < 0):
        raise ValueError("Maximum distance must be a non-negative number.")
        
    results = []
    
    for _, row in stops.iterrows():
        dist = haversine_km(latitude, longitude, row.lat, row.lon)
        
        if max_distance_km is not None and dist > max_distance_km:
            continue
            
        walk_time = (dist / WALK_SPEED_KMH) * 60.0
        
        results.append({
            "stop_id": row.stop_id,
            "name": row.stop_name,
            "latitude": row.lat,
            "longitude": row.lon,
            "distance_km": round(dist, 3),
            "walking_time_min": round(walk_time, 2)
        })
        
    # Sort strictly by distance
    results.sort(key=lambda x: x["distance_km"])
    
    return results[:limit]

def add_temporary_connectors(
    base_graph: nx.DiGraph,
    user_node_id: str,
    user_lat: float,
    user_lon: float,
    nearest_stops: List[Dict[str, Any]],
    direction: str = "origin"
) -> nx.DiGraph:
    """
    Creates a copy of the base graph and adds a temporary user node connected to the nearest stops via walking edges.
    
    Args:
        base_graph: nx.DiGraph, the existing transit graph
        user_node_id: str, the unique ID for the temporary node (e.g., "__USER_ORIGIN__")
        user_lat: float, latitude of the user
        user_lon: float, longitude of the user
        nearest_stops: List[Dict], the list of nearest stop dictionaries returned by find_nearest_stops
        direction: str, either "origin" (node -> stops) or "destination" (stops -> node)
        
    Returns:
        A new nx.DiGraph containing the temporary nodes and edges.
    """
    if direction not in ("origin", "destination"):
        raise ValueError("Direction must be 'origin' or 'destination'.")
        
    # Always operate on a copy to preserve the integrity of the original graph dataset
    G = base_graph.copy()
    
    # Add the temporary user node with actual user coordinates for A* compatibility
    G.add_node(user_node_id, name="User Location", mode="walk", lat=float(user_lat), lon=float(user_lon))
    
    for stop in nearest_stops:
        stop_id = stop["stop_id"]
        dist = stop["distance_km"]
        time_min = stop["walking_time_min"]
        
        # Consistent schema with src/graph/graph_builder.py
        edge_attrs = {
            "mode": "walk",
            "time": float(time_min),
            "cost": 0.0,
            "distance": float(dist)
        }
        
        if direction == "origin":
            G.add_edge(user_node_id, stop_id, **edge_attrs)
        else:
            G.add_edge(stop_id, user_node_id, **edge_attrs)
            
    return G
