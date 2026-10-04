import sys
from pathlib import Path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pandas as pd
from src.graph.graph_builder import get_default_graph, resolve_stop
from src.algorithms.k_shortest import k_shortest_routes
from src.algorithms.multicriteria import rank_and_evaluate_routes
from src.algorithms.constraints import filter_routes_by_constraints

def print_filter_results(test_name, budget, max_time, result, ranked_df):
    print(f"\n--- {test_name} ---")
    print(f"Budget: {budget}")
    print(f"Max time: {max_time}")
    
    feasible = result["feasible"]
    rejected = result["rejected"]
    
    print(f"Feasible routes: {len(feasible)}")
    print(f"Rejected routes: {len(rejected)}")
    
    for r in feasible:
        print(f"R(cost={r.total_cost}, time={r.total_time}) -> ACCEPT")
    for rej in rejected:
        r = rej["route"]
        print(f"R(cost={r.total_cost}, time={r.total_time}) -> REJECT ({', '.join(rej['reasons'])})")
        
    if not ranked_df.empty:
        print("\nRanked Feasible Routes:")
        cols = ["rank", "time_min", "cost_bdt", "score"]
        print(ranked_df[cols].to_string(index=False))
    else:
        print("\nNo route satisfies the current constraints.")


def run_phase4_validation():
    print("Building graph for constraints validation...")
    G, stops_df = get_default_graph()
    
    origin_id = resolve_stop(stops_df, "Uttara", mode="metro")
    dest_id = resolve_stop(stops_df, "Motijheel", mode="metro")

    print("\nGenerating 5 candidate routes (Yen's K-Shortest)...")
    candidates = k_shortest_routes(G, origin_id, dest_id, k=5)
    print(f"Original candidates: {len(candidates)}")
    for r in candidates:
        print(f" - time={r.total_time}, cost={r.total_cost}")

    # TEST A - No constraints
    res_A = filter_routes_by_constraints(candidates, budget=None, max_time=None)
    assert len(res_A["feasible"]) == 5
    ranked_A = rank_and_evaluate_routes(res_A["feasible"])
    print_filter_results("TEST A - No constraints", None, None, res_A, ranked_A)
    assert abs(ranked_A.iloc[0]["score"] - 0.8) < 1e-6
    assert abs(ranked_A.iloc[-1]["score"] - 0.15) < 1e-6
    
    # TEST B - Budget only (rejects cost=120)
    res_B = filter_routes_by_constraints(candidates, budget=115, max_time=None)
    for r in res_B["feasible"]:
        assert r.total_cost <= 115
    ranked_B = rank_and_evaluate_routes(res_B["feasible"])
    print_filter_results("TEST B - Budget only (<=115)", 115, None, res_B, ranked_B)

    # TEST C - Time only (rejects time=43, accepts 28, 39)
    res_C = filter_routes_by_constraints(candidates, budget=None, max_time=40)
    for r in res_C["feasible"]:
        assert r.total_time <= 40
    ranked_C = rank_and_evaluate_routes(res_C["feasible"])
    print_filter_results("TEST C - Time only (<=40)", None, 40, res_C, ranked_C)
    
    # TEST D - Budget + Time (budget=110, time=40 -> accepts cost=110/time=39)
    res_D = filter_routes_by_constraints(candidates, budget=110, max_time=40)
    for r in res_D["feasible"]:
        assert r.total_cost <= 110 and r.total_time <= 40
    ranked_D = rank_and_evaluate_routes(res_D["feasible"])
    print_filter_results("TEST D - Budget + Time (<=110 BDT, <=40 min)", 110, 40, res_D, ranked_D)

    # TEST E - Exact boundary (cost=120, time=28)
    res_E = filter_routes_by_constraints(candidates, budget=120, max_time=28)
    assert len(res_E["feasible"]) == 1
    ranked_E = rank_and_evaluate_routes(res_E["feasible"])
    print_filter_results("TEST E - Exact boundary (budget=120, time=28)", 120, 28, res_E, ranked_E)

    # TEST F - No feasible route
    res_F = filter_routes_by_constraints(candidates, budget=100, max_time=20)
    assert len(res_F["feasible"]) == 0
    ranked_F = rank_and_evaluate_routes(res_F["feasible"])
    print_filter_results("TEST F - No feasible route (budget=100, time=20)", 100, 20, res_F, ranked_F)
    assert ranked_F.empty

    # TEST G - Invalid budget
    try:
        filter_routes_by_constraints(candidates, budget=-1, max_time=None)
        assert False, "Should raise ValueError for negative budget"
    except ValueError as e:
        print(f"\nTEST G - Invalid budget (-1): Caught {e}")
        
    # TEST H - Invalid max time
    try:
        filter_routes_by_constraints(candidates, budget=None, max_time=-5)
        assert False, "Should raise ValueError for negative time"
    except ValueError as e:
        print(f"TEST H - Invalid max time (-5): Caught {e}")

    # TEST I - Only one feasible route (score check)
    res_I = filter_routes_by_constraints(candidates, budget=110, max_time=39)
    assert len(res_I["feasible"]) == 1
    ranked_I = rank_and_evaluate_routes(res_I["feasible"])
    print_filter_results("TEST I - Single Feasible Route", 110, 39, res_I, ranked_I)
    assert not pd.isna(ranked_I.iloc[0]["score"])

    print("\nPhase 4 Validation PASSED")

if __name__ == "__main__":
    run_phase4_validation()
