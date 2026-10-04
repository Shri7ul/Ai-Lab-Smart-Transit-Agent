import sys
from pathlib import Path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import networkx as nx
from src.graph.graph_builder import get_default_graph
from src.algorithms.dijkstra import dijkstra_route
from src.algorithms.astar import find_astar_path, time_heuristic, get_max_speed_km_per_min

def run_phase3_validation():
    print("Building graph for A* exhaustive validation...")
    G, stops_df = get_default_graph()
    
    assert G.number_of_nodes() == 16, f"Expected 16 nodes, got {G.number_of_nodes()}"
    assert G.number_of_edges() == 44, f"Expected 44 edges, got {G.number_of_edges()}"
    print("Graph size preserved: 16 nodes, 44 edges.")

    print("\n--- Baseline Test (UTR_MTR to MTJ_MTR) ---")
    d_path, d_time = dijkstra_route(G, "UTR_MTR", "MTJ_MTR")
    a_path, a_time = find_astar_path(G, "UTR_MTR", "MTJ_MTR")
    print(f"Dijkstra Time: {d_time} min")
    print(f"A* Time:       {a_time} min")
    assert abs(d_time - 28.0) < 1e-9, f"Dijkstra time expected 28.0, got {d_time}"
    assert abs(a_time - 28.0) < 1e-9, f"A* time expected 28.0, got {a_time}"

    print("\n--- Exhaustive A* vs Dijkstra Validation ---")
    nodes = list(G.nodes)
    total_pairs = len(nodes) * len(nodes)
    reachable_pairs = 0
    unreachable_pairs = 0
    matches = 0
    mismatches = 0
    max_admissibility_violation = 0.0

    max_speed = get_max_speed_km_per_min(G)
    print(f"Computed maximum effective speed: {max_speed:.4f} km/min")

    for u in nodes:
        for v in nodes:
            if u == v:
                reachable_pairs += 1
                d_p, d_t = dijkstra_route(G, u, v)
                a_p, a_t = find_astar_path(G, u, v)
                if abs(d_t - a_t) < 1e-9:
                    matches += 1
                else:
                    mismatches += 1
                    print(f"Mismatch: {u} -> {v} (same node). Dijkstra={d_t}, A*={a_t}")
                continue
                
            has_path = nx.has_path(G, u, v)
            if not has_path:
                unreachable_pairs += 1
                try:
                    find_astar_path(G, u, v)
                    mismatches += 1
                    print(f"Mismatch: {u} -> {v} (unreachable). A* found path!")
                except nx.NetworkXNoPath:
                    matches += 1
            else:
                reachable_pairs += 1
                d_p, d_t = dijkstra_route(G, u, v)
                a_p, a_t = find_astar_path(G, u, v)
                
                if abs(d_t - a_t) < 1e-9:
                    matches += 1
                else:
                    mismatches += 1
                    print(f"Mismatch: {u} -> {v}. Dijkstra={d_t}, A*={a_t}")
                
                h_val = time_heuristic(G, u, v, max_speed)
                violation = h_val - d_t
                if violation > max_admissibility_violation:
                    max_admissibility_violation = violation
                    
                if violation > 1e-9:
                    print(f"Admissibility violation! {u}->{v}. h(u)={h_val}, true_cost={d_t}")

    print(f"\n--- Exhaustive Validation Results ---")
    print(f"Total ordered pairs checked: {total_pairs}")
    print(f"Reachable pairs:             {reachable_pairs}")
    print(f"Unreachable pairs:           {unreachable_pairs}")
    print(f"A*/Dijkstra matches:         {matches}")
    print(f"A*/Dijkstra mismatches:      {mismatches}")
    print(f"Max admissibility violation: {max_admissibility_violation:.9f}")

    assert mismatches == 0, f"Validation failed with {mismatches} mismatches."
    assert max_admissibility_violation <= 1e-9, f"Admissibility violation found!"
    print("\nPhase 3 Exhaustive Validation PASSED")

if __name__ == "__main__":
    run_phase3_validation()
