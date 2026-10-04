"""
Dijkstra's Algorithm implementation.
"""
import networkx as nx
from typing import Tuple, List

def dijkstra_route(graph: nx.DiGraph, origin: str, destination: str,
                   weight: str = "time") -> Tuple[List[str], float]:
    """Baseline single-objective shortest path using Dijkstra."""
    path = nx.dijkstra_path(graph, origin, destination, weight=weight)
    length = nx.dijkstra_path_length(graph, origin, destination, weight=weight)
    return path, length
