"""
Multi-criteria route evaluation and Pareto dominance analysis.
"""
import numpy as np
import pandas as pd
from typing import List, Dict
from src.graph.models import Route

DEFAULT_WEIGHTS = {"time": 0.45, "cost": 0.20, "transfers": 0.20, "walking": 0.15}

def routes_to_dataframe(routes: List[Route]) -> pd.DataFrame:
    rows = []
    for i, r in enumerate(routes, start=1):
        rows.append({
            "route": f"R{i}",
            "mode_sequence": " -> ".join(r.mode_sequence),
            "num_stops": len(r.path),
            "time_min": r.total_time,
            "cost_bdt": r.total_cost,
            "transfers": r.num_transfers,
            "walk_km": round(r.walking_distance, 2),
        })
    return pd.DataFrame(rows)

def normalize_min_max(values: np.ndarray) -> np.ndarray:
    """Min-max normalize an array to [0, 1]. Returns all-zero if there is no spread."""
    vmin, vmax = values.min(), values.max()
    if np.isclose(vmax, vmin):
        return np.zeros_like(values, dtype=float)
    return (values - vmin) / (vmax - vmin)

def score_routes(metrics: pd.DataFrame, weights: Dict[str, float]) -> pd.DataFrame:
    """Normalize metrics and compute the weighted objective J for each route."""
    assert abs(sum(weights.values()) - 1.0) < 1e-6, "weights must sum to 1.0"

    df = metrics.copy()
    df["time_norm"] = normalize_min_max(df["time_min"].to_numpy(dtype=float))
    df["cost_norm"] = normalize_min_max(df["cost_bdt"].to_numpy(dtype=float))
    df["transfers_norm"] = normalize_min_max(df["transfers"].to_numpy(dtype=float))
    df["walk_norm"] = normalize_min_max(df["walk_km"].to_numpy(dtype=float))

    df["J"] = (
        weights["time"] * df["time_norm"]
        + weights["cost"] * df["cost_norm"]
        + weights["transfers"] * df["transfers_norm"]
        + weights["walking"] * df["walk_norm"]
    )
    df["score"] = 1 - df["J"]
    return df

def pareto_optimal_mask(df: pd.DataFrame,
                          cols: List[str] = ["time_min", "cost_bdt", "transfers", "walk_km"]
                          ) -> np.ndarray:
    """Return a boolean mask marking Pareto-optimal rows (all `cols` minimized)."""
    values = df[cols].to_numpy(dtype=float)
    n = len(values)
    is_optimal = np.ones(n, dtype=bool)
    for i in range(n):
        for j in range(n):
            if i == j:
                continue
            at_least_as_good = np.all(values[j] <= values[i])
            strictly_better = np.any(values[j] < values[i])
            if at_least_as_good and strictly_better:
                is_optimal[i] = False
                break
    return is_optimal

def rank_and_evaluate_routes(routes: List[Route], weights: Dict[str, float] | None = None) -> pd.DataFrame:
    """End-to-end evaluation: metrics -> score -> pareto -> rank."""
    if not routes:
        return pd.DataFrame()
    if weights is None:
        weights = DEFAULT_WEIGHTS
        
    m_df = routes_to_dataframe(routes)
    s_df = score_routes(m_df, weights)
    s_df["pareto_optimal"] = pareto_optimal_mask(s_df)
    
    r_df = s_df.sort_values("score", ascending=False).reset_index(drop=True)
    r_df.insert(0, "rank", r_df.index + 1)
    return r_df
