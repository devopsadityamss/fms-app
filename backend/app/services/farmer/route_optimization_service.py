# backend/app/services/farmer/route_optimization_service.py

from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
import math

from app.services.farmer.equipment_service import (
    compute_equipment_operating_cost,
    compute_equipment_health,
    equipment_workload_pressure_score
)
from app.services.farmer.fuel_analytics_service import analyze_fuel_usage
from app.services.farmer.operator_behavior_service import compute_operator_behavior


# ------------------------------------------------------------
# Utility: Haversine distance (km)
# ------------------------------------------------------------
def haversine(lat1, lon1, lat2, lon2):
    R = 6371.0
    dlat = math.radians(lat2-lat1)
    dlon = math.radians(lon2-lon1)
    a = (
        math.sin(dlat/2)**2 +
        math.cos(math.radians(lat1)) *
        math.cos(math.radians(lat2)) *
        math.sin(dlon/2)**2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    return R * c


# ------------------------------------------------------------
# INTERNAL: compute pairwise distance matrix for fields
# ------------------------------------------------------------
def _compute_distance_matrix(tasks: List[Dict[str, Any]]) -> List[List[float]]:
    N = len(tasks)
    dist = [[0.0]*N for _ in range(N)]
    for i in range(N):
        for j in range(N):
            if i == j:
                dist[i][j] = 0.0
                continue
            ti, tj = tasks[i], tasks[j]
            dist[i][j] = haversine(
                float(ti["lat"]), float(ti["lon"]),
                float(tj["lat"]), float(tj["lon"])
            )
    return dist


# ------------------------------------------------------------
# Scoring weights
# ------------------------------------------------------------
DEFAULT_WEIGHTS = {
    "distance": 0.50,
    "fuel": 0.25,
    "wear": 0.15,
    "operator": 0.10
}


# ------------------------------------------------------------
# Greedy TSP heuristic + local improvement
# ------------------------------------------------------------
def _greedy_route(dist_matrix: List[List[float]], start_idx: int = 0) -> List[int]:
    N = len(dist_matrix)
    visited = set([start_idx])
    order = [start_idx]

    while len(visited) < N:
        last = order[-1]
        # choose nearest unvisited
        candidates = [(dist_matrix[last][j], j) for j in range(N) if j not in visited]
        next_node = min(candidates)[1]
        order.append(next_node)
        visited.add(next_node)

    return order


def _two_opt(route: List[int], dist_matrix: List[List[float]]) -> List[int]:
    """
    2-opt improvement loop (simple version).
    """
    improved = True
    best = route
    best_cost = _route_dist_cost(best, dist_matrix)
    N = len(route)

    while improved:
        improved = False
        for i in range(1, N-2):
            for k in range(i+1, N):
                new = best[:]
                new[i:k] = reversed(best[i:k])  # swap segment
                new_cost = _route_dist_cost(new, dist_matrix)
                if new_cost < best_cost:
                    best = new
                    best_cost = new_cost
                    improved = True
        route = best

    return best


def _route_dist_cost(route: List[int], dist_matrix: List[List[float]]) -> float:
    cost = 0.0
    for i in range(len(route)-1):
        cost += dist_matrix[route[i]][route[i+1]]
    return cost


# ------------------------------------------------------------
# Effective route scoring (distance + fuel + wear + operator)
# ------------------------------------------------------------
def _score_route(
    route: List[int],
    tasks: List[Dict[str, Any]],
    dist_matrix: List[List[float]],
    equipment_id: str,
    weights: Dict[str, float]
) -> Dict[str, Any]:

    # 1) total distance
    total_distance = _route_dist_cost(route, dist_matrix)

    # 2) fuel burn rate
    fuel = analyze_fuel_usage(equipment_id) or {}
    lph = fuel.get("avg_hourly_fuel", 3.0)  # fallback 3 L/hr
    # assume travel speed ~ 15 km/h → hours = dist / speed
    hours_travel = total_distance / 15.0
    fuel_used = hours_travel * lph

    # 3) wear proxy
    health = compute_equipment_health(equipment_id) or {}
    wear_score = (100 - health.get("health_score", 70)) / 100.0
    wear_penalty = wear_score * total_distance  # more distance → more wear impact

    # 4) operator behavior
    # choose operator from first task (if provided)
    operator_id = tasks[route[0]].get("operator_id")
    if operator_id:
        op = compute_operator_behavior(operator_id)
        operator_risk = (100 - op.get("final_behavior_score", 50)) / 100.0
    else:
        operator_risk = 0.2

    # weighted score (lower is better)
    total_score = (
        weights["distance"] * total_distance +
        weights["fuel"] * fuel_used +
        weights["wear"] * wear_penalty +
        weights["operator"] * operator_risk
    )

    return {
        "score": round(total_score, 3),
        "total_km": round(total_distance, 2),
        "fuel_liters_est": round(fuel_used, 2),
        "wear_penalty": round(wear_penalty, 3),
        "operator_penalty": round(operator_risk, 3)
    }


# ------------------------------------------------------------
# MAIN ENTRY: Optimize route for tasks
# ------------------------------------------------------------
def optimize_route_for_tasks(
    equipment_id: str,
    tasks: List[Dict[str, Any]],
    weight_config: Optional[Dict[str, float]] = None
) -> Dict[str, Any]:
    """
    tasks = [
      { "task_id": "...", "lat": 12.9, "lon": 77.5, "estimated_hours": 3, "operator_id": "op1" },
      ...
    ]
    """

    if not tasks:
        return {"status": "no_tasks"}

    weights = DEFAULT_WEIGHTS.copy()
    if weight_config:
        for k, v in weight_config.items():
            if k in weights:
                weights[k] = float(v)

    # compute pairwise distances
    dist_matrix = _compute_distance_matrix(tasks)

    # greedy + 2-opt
    initial = _greedy_route(dist_matrix)
    improved = _two_opt(initial, dist_matrix)

    # score route
    scored = _score_route(improved, tasks, dist_matrix, equipment_id, weights)

    # convert route index → task list order
    ordered_tasks = [tasks[i] for i in improved]

    return {
        "equipment_id": equipment_id,
        "optimized_route_indices": improved,
        "optimized_tasks": ordered_tasks,
        "metrics": scored,
        "weights_used": weights,
        "generated_at": datetime.utcnow().isoformat()
    }
