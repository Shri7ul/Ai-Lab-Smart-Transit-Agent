from typing import Any

from src.graph.models import Route


def filter_routes_by_constraints(
    routes: list[Route],
    budget: float | None = None,
    max_time: float | None = None,
) -> dict[str, list[Any]]:
    """
    Filters a list of candidate routes based on hard constraints (budget and/or maximum travel time).
    Returns a dictionary with 'feasible' routes and a list of 'rejected' routes with rejection reasons.
    """
    if budget is not None and (not isinstance(budget, (int, float)) or budget < 0):
        raise ValueError("Budget must be a non-negative number.")
    
    if max_time is not None and (not isinstance(max_time, (int, float)) or max_time < 0):
        raise ValueError("Maximum time must be a non-negative number.")
    
    feasible = []
    rejected = []

    for route in routes:
        reasons = []
        
        if budget is not None and route.total_cost > budget:
            reasons.append("budget_exceeded")
            
        if max_time is not None and route.total_time > max_time:
            reasons.append("time_exceeded")
            
        if reasons:
            rejected.append({"route": route, "reasons": reasons})
        else:
            feasible.append(route)
            
    return {
        "feasible": feasible,
        "rejected": rejected
    }
