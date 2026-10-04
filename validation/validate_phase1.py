import sys
from pathlib import Path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pandas as pd
from typing import Optional
from src.graph.graph_builder import get_default_graph, resolve_stop
from src.algorithms.dijkstra import dijkstra_route
from src.algorithms.k_shortest import k_shortest_routes
from src.algorithms.multicriteria import rank_and_evaluate_routes, DEFAULT_WEIGHTS

def run_validation():
    print("Building graph...")
    G, stops_df = get_default_graph()
    print(f"Graph built with {G.number_of_nodes()} nodes and {G.number_of_edges()} edges.")
    
    origin_name = "Uttara"
    dest_name = "Motijheel"
    try:
        origin_id = resolve_stop(stops_df, origin_name, mode="metro")
        dest_id = resolve_stop(stops_df, dest_name, mode="metro")
    except ValueError as e:
        print(f"Error resolving stops: {e}")
        return

    print(f"\nFinding shortest path (Dijkstra) from {origin_id} to {dest_id}...")
    try:
        path, length = dijkstra_route(G, origin_id, dest_id)
        print(f"Path: {' -> '.join(path)}")
        print(f"Length (time): {length} min")
    except Exception as e:
        print(f"Dijkstra failed: {e}")
        return

    print(f"\nGenerating 5 candidate routes (Yen's K-Shortest)...")
    routes = k_shortest_routes(G, origin_id, dest_id, k=5)
    print(f"Generated {len(routes)} candidates.")
    
    print("\nScoring and ranking routes...")
    ranked_df = rank_and_evaluate_routes(routes, DEFAULT_WEIGHTS)
    
    print("\nFinal Ranked Recommendations:")
    display_df = ranked_df[["rank", "route", "mode_sequence", "time_min", "cost_bdt", "transfers", "walk_km", "score", "pareto_optimal"]]
    print(display_df.to_string(index=False))

if __name__ == "__main__":
    run_validation()
