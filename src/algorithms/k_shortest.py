"""
Yen's K-Shortest Paths algorithm.
"""
import networkx as nx
from typing import List
from src.graph.models import Route, Leg

def path_to_route(graph: nx.DiGraph, path: List[str]) -> Route:
    legs = []
    for u, v in zip(path, path[1:]):
        d = graph[u][v]
        legs.append(Leg(u, v, d["mode"], d["time"], d["cost"], d["distance"]))
    return Route(path=path, legs=legs)

def k_shortest_routes(graph: nx.DiGraph, origin: str, destination: str,
                       k: int = 5, weight: str = "time") -> List[Route]:
    """Generate up to k loop-less candidate routes using Yen's algorithm."""
    routes = []
    try:
        path_generator = nx.shortest_simple_paths(graph, origin, destination, weight=weight)
        for i, path in enumerate(path_generator):
            if i >= k:
                break
            routes.append(path_to_route(graph, path))
    except nx.NetworkXNoPath:
        pass
    return routes
