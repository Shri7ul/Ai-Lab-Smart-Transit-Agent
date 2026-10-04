import sys
from pathlib import Path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pandas as pd
from src.graph.data_loader import load_transit_data
from src.graph.graph_builder import get_default_graph, resolve_stop
from src.algorithms.dijkstra import dijkstra_route
from src.algorithms.k_shortest import k_shortest_routes
from src.algorithms.multicriteria import rank_and_evaluate_routes, DEFAULT_WEIGHTS

def run_phase2_validation():
    print("Testing data loader...")
    try:
        stops_df, edges_df = load_transit_data()
        print(f"Loaded {len(stops_df)} stops and {len(edges_df)} transit edges from JSON successfully.")
        assert len(stops_df) == 16, f"Expected 16 stops, got {len(stops_df)}"
    except Exception as e:
        print(f"Data loading failed: {e}")
        return

    print("\nBuilding graph...")
    G, stops_df = get_default_graph()
    print(f"Graph built with {G.number_of_nodes()} nodes and {G.number_of_edges()} edges.")
    assert G.number_of_nodes() == 16, f"Expected 16 nodes, got {G.number_of_nodes()}"
    assert G.number_of_edges() == 44, f"Expected 44 edges, got {G.number_of_edges()}"
    
    origin_name = "Uttara"
    dest_name = "Motijheel"
    origin_id = resolve_stop(stops_df, origin_name, mode="metro")
    dest_id = resolve_stop(stops_df, dest_name, mode="metro")

    print(f"\nFinding shortest path (Dijkstra) from {origin_id} to {dest_id}...")
    path, length = dijkstra_route(G, origin_id, dest_id)
    print(f"Path: {' -> '.join(path)}")
    print(f"Length (time): {length} min")
    assert length == 28.0, f"Expected length 28.0, got {length}"

    print(f"\nGenerating 5 candidate routes (Yen's K-Shortest)...")
    routes = k_shortest_routes(G, origin_id, dest_id, k=5)
    print(f"Generated {len(routes)} candidates.")
    assert len(routes) == 5, f"Expected 5 routes, got {len(routes)}"
    
    print("\nScoring and ranking routes...")
    ranked_df = rank_and_evaluate_routes(routes, DEFAULT_WEIGHTS)
    
    print("\nFinal Ranked Recommendations:")
    display_df = ranked_df[["rank", "route", "mode_sequence", "time_min", "cost_bdt", "transfers", "walk_km", "score", "pareto_optimal"]]
    print(display_df.to_string(index=False))
    
    print("\nPhase 2 Validation PASSED")

if __name__ == "__main__":
    run_phase2_validation()
