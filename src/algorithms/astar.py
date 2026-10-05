"""
A* Search Algorithm implementation.
"""
import heapq
import networkx as nx
from typing import Tuple, List, Dict
from src.utils.distance import haversine_km

def get_max_speed_km_per_min(graph: nx.DiGraph) -> float:
    """
    Calculate the maximum effective speed (km/min) across all edges in the graph.
    Uses Haversine distance between nodes to guarantee consistency with the heuristic.
    This is used to compute an admissible time-based heuristic.
    """
    max_speed = 0.0
    for u, v, data in graph.edges(data=True):
        time = data.get("time", 0.0)
        if time > 0:
            try:
                lat1, lon1 = graph.nodes[u]["lat"], graph.nodes[u]["lon"]
                lat2, lon2 = graph.nodes[v]["lat"], graph.nodes[v]["lon"]
                geodesic_distance_km = haversine_km(lat1, lon1, lat2, lon2)
                speed = geodesic_distance_km / time
                if speed > max_speed:
                    max_speed = speed
            except KeyError:
                continue
    # Fallback if no valid edges exist
    return max_speed if max_speed > 0 else 1.0

def time_heuristic(graph: nx.DiGraph, current: str, target: str, max_speed_km_per_min: float) -> float:
    """
    Admissible heuristic for time-based A*.
    Uses Haversine straight-line distance divided by the maximum possible speed
    to guarantee a lower-bound on travel time.
    """
    try:
        lat1, lon1 = graph.nodes[current]["lat"], graph.nodes[current]["lon"]
        lat2, lon2 = graph.nodes[target]["lat"], graph.nodes[target]["lon"]
    except KeyError:
        return 0.0  # Fallback safely to Dijkstra if coordinates are missing

    dist_km = haversine_km(lat1, lon1, lat2, lon2)
    return dist_km / max_speed_km_per_min

def find_astar_path(graph: nx.DiGraph, source: str, destination: str, weight: str = "time") -> Tuple[List[str], float]:
    """
    A* shortest path search guided by a heuristic.
    
    g(n) = actual accumulated cost (e.g. time) from source
    h(n) = estimated remaining cost to destination
    f(n) = g(n) + h(n)
    """
    if source not in graph:
        raise ValueError(f"Source node {source!r} not found in graph.")
    if destination not in graph:
        raise ValueError(f"Destination node {destination!r} not found in graph.")
        
    if source == destination:
        return [source], 0.0

    # For unsupported weights, behave like Dijkstra by using a zero heuristic
    if weight == "time":
        max_speed = get_max_speed_km_per_min(graph)
        def heuristic(u, v): return time_heuristic(graph, u, v, max_speed)
    else:
        def heuristic(u, v): return 0.0
        
    # Priority queue: stores tuples of (f_score, node)
    open_set = []
    heapq.heappush(open_set, (0.0, source))
    
    # g_score: lowest cost from source to node
    g_score: Dict[str, float] = {source: 0.0}
    
    # came_from: for path reconstruction
    came_from: Dict[str, str] = {}
    
    while open_set:
        current_f, current = heapq.heappop(open_set)
        
        if current == destination:
            path = []
            while current in came_from:
                path.append(current)
                current = came_from[current]
            path.append(source)
            path.reverse()
            return path, g_score[destination]
            
        # Optional: We could ignore nodes if current_f > g_score[current] + heuristic
        # but typical A* implementation handles this via g_score updates
        
        for neighbor in graph.successors(current):
            edge_weight = graph[current][neighbor].get(weight, float('inf'))
            if edge_weight < 0:
                raise ValueError("Graph contains negative edge weights.")
                
            tentative_g = g_score[current] + edge_weight
            
            if neighbor not in g_score or tentative_g < g_score[neighbor]:
                came_from[neighbor] = current
                g_score[neighbor] = tentative_g
                f_score = tentative_g + heuristic(neighbor, destination)
                heapq.heappush(open_set, (f_score, neighbor))
                
    raise nx.NetworkXNoPath(f"No path between {source} and {destination}.")
