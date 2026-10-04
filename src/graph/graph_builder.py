"""
Multimodal graph construction for the Smart Transit project.
"""
import pandas as pd
import networkx as nx
from typing import Tuple, Optional
from src.utils.distance import haversine_km
from src.graph.data_loader import load_transit_data

WALK_SPEED_KMH = 4.5
MAX_WALK_DISTANCE_KM = 0.6

def generate_walking_edges(stops: pd.DataFrame) -> pd.DataFrame:
    walk_edges_data = []
    for i, row_a in stops.iterrows():
        for j, row_b in stops.iterrows():
            if row_a.stop_id == row_b.stop_id:
                continue
            same_area = row_a.stop_name == row_b.stop_name
            dist_km = haversine_km(row_a.lat, row_a.lon, row_b.lat, row_b.lon)
            if same_area or dist_km <= MAX_WALK_DISTANCE_KM:
                walk_time_min = max(1, round((dist_km / WALK_SPEED_KMH) * 60))
                walk_edges_data.append(
                    (row_a.stop_id, row_b.stop_id, "walk", walk_time_min, 0, round(dist_km, 2))
                )
    walk_edges = pd.DataFrame(
        walk_edges_data, columns=["from", "to", "mode", "travel_time", "cost", "distance"]
    )
    walk_edges = walk_edges.drop_duplicates(subset=["from", "to"]).reset_index(drop=True)
    return walk_edges

def build_graph(stops_df: pd.DataFrame, edges_df: pd.DataFrame) -> nx.DiGraph:
    """Build a weighted directed multimodal transit graph from edge and stop tables."""
    G = nx.DiGraph()
    for _, stop in stops_df.iterrows():
        G.add_node(stop.stop_id, name=stop.stop_name, mode=stop["mode"],
                   lat=stop.lat, lon=stop.lon)
    for _, e in edges_df.iterrows():
        if G.has_edge(e["from"], e["to"]):
            if e["travel_time"] >= G[e["from"]][e["to"]]["time"]:
                continue
        G.add_edge(
            e["from"], e["to"],
            mode=e["mode"], time=float(e["travel_time"]),
            cost=float(e["cost"]), distance=float(e["distance"]),
        )
    return G

def get_default_graph() -> Tuple[nx.DiGraph, pd.DataFrame]:
    stops, transit_edges = load_transit_data()
    walk_edges = generate_walking_edges(stops)
    edges = pd.concat([transit_edges, walk_edges], ignore_index=True)
    edges["distance"] = edges["distance"].round(2)
    return build_graph(stops, edges), stops

def resolve_stop(stops_df: pd.DataFrame, name_or_id: str, mode: Optional[str] = None) -> str:
    """Resolve a human-readable stop name (or an exact stop_id) to a stop_id."""
    if name_or_id in stops_df["stop_id"].values:
        return name_or_id
    matches = stops_df[stops_df.stop_name.str.lower() == name_or_id.lower()]
    if mode is not None:
        matches = matches[matches["mode"] == mode]
    if matches.empty:
        raise ValueError(f"Unknown stop or station: {name_or_id!r}")
    return matches.iloc[0].stop_id

