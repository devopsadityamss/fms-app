# backend/app/services/farmer/peer_benchmark_service.py

from datetime import datetime
from threading import Lock
from typing import Dict, Any, List, Optional
import statistics

# reuse internal services where available
try:
    from app.services.farmer.yield_forecasting_service import forecast_yield_for_unit
except Exception:
    forecast_yield_for_unit = None

try:
    from app.services.farmer.profitability_service import compute_profitability
except Exception:
    compute_profitability = None

try:
    from app.services.farmer.financial_ledger_service import compute_cashflow_summary
except Exception:
    compute_cashflow_summary = None

# unit store (to compare own units)
try:
    from app.services.farmer.unit_service import _unit_store
except Exception:
    _unit_store = {}

# In-memory peer registry (simple statistics per peer farm)
# peer_id -> { peer_id, name, location (optional), metrics: { yield_q_per_acre, cost_per_acre, profit_margin_pct, irrigation_eff_l_per_acre }, meta... }
_peer_store: Dict[str, Dict[str, Any]] = {}
_peer_lock = Lock()


def register_peer(peer_id: str, name: str, location: Optional[str] = None, metrics: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Register or update a peer farm summary. Metrics should be aggregated per-acre or per-season:
      metrics = {
        "yield_q_per_acre": 18.5,
        "cost_per_acre": 25000.0,
        "profit_margin_pct": 18.5,
        "irrigation_l_per_acre": 50000.0
      }
    """
    rec = {
        "peer_id": peer_id,
        "name": name,
        "location": location,
        "metrics": metrics or {},
        "registered_at": datetime.utcnow().isoformat()
    }
    with _peer_lock:
        _peer_store[peer_id] = rec
    return rec


def list_peers() -> Dict[str, Any]:
    with _peer_lock:
        return {"count": len(_peer_store), "peers": list(_peer_store.values())}


def bulk_import_peers(peers: List[Dict[str, Any]]) -> Dict[str, Any]:
    added = 0
    for p in peers:
        pid = p.get("peer_id") or p.get("id")
        if not pid:
            continue
        register_peer(pid, p.get("name", pid), location=p.get("location"), metrics=p.get("metrics"))
        added += 1
    return {"imported": added, "total_peers": len(_peer_store)}


# ---- utilities ----
def _median_and_percentile_list(values: List[float]) -> Dict[str, Any]:
    if not values:
        return {"median": None, "values": []}
    med = statistics.median(values)
    return {"median": round(med, 3), "values": [round(v, 3) for v in values]}


def _percentile_rank(value: float, values: List[float]) -> Optional[float]:
    """
    Return percentile rank of value within values (0-100). If values empty, return None.
    """
    if not values:
        return None
    sorted_vals = sorted(values)
    # compute fraction of peers <= value
    less_equal = sum(1 for v in sorted_vals if v <= value)
    rank = (less_equal / len(sorted_vals)) * 100
    return round(rank, 2)


# ---- Core benchmarking: compute peer distributions ----
def _gather_peer_distributions() -> Dict[str, List[float]]:
    with _peer_lock:
        peers = list(_peer_store.values())
    dist = {
        "yield_q_per_acre": [],
        "cost_per_acre": [],
        "profit_margin_pct": [],
        "irrigation_l_per_acre": []
    }
    for p in peers:
        m = p.get("metrics", {}) or {}
        for k in dist.keys():
            v = m.get(k)
            if v is None:
                continue
            try:
                dist[k].append(float(v))
            except Exception:
                continue
    return dist


# ---- Compute metrics for a local unit by reusing services if present ----
def _compute_unit_metrics(unit_id: str) -> Dict[str, Any]:
    """
    Best-effort compute:
      - yield_q_per_acre via forecast_yield_for_unit
      - cost_per_acre via profitability_service (cost_breakdown / area)
      - profit_margin_pct via profitability_service
      - irrigation_l_per_acre not computed unless irrigation module provides; left None otherwise
    """
    res = {
        "unit_id": unit_id,
        "yield_q_per_acre": None,
        "cost_per_acre": None,
        "profit_margin_pct": None,
        "irrigation_l_per_acre": None
    }

    # yield
    try:
        if forecast_yield_for_unit:
            y = forecast_yield_for_unit(unit_id)
            if y and "expected_yield_quintal" in y and "area_acre" in y:
                q = float(y["expected_yield_quintal"] or 0)
                area = float(y.get("area_acre") or 1.0)
                res["yield_q_per_acre"] = round(q / max(1e-6, area), 3)
    except Exception:
        pass

    # profitability (cost & margin)
    try:
        if compute_profitability:
            # market price optional; compute_profitability will still return structure (it calls yield service internally)
            pf = compute_profitability(unit_id, market_price_per_quintal=0.0)
            cost_tot = pf.get("cost_breakdown", {}).get("total_cost")
            area = float(pf.get("area_acre") or pf.get("area") or 1.0) if isinstance(pf.get("area_acre"), (int,float)) else None
            # If area not available in pf, try to retrieve from unit store
            if area is None:
                try:
                    unit = _unit_store.get(unit_id, {})
                    area = float(unit.get("area", 1.0) or 1.0)
                except Exception:
                    area = 1.0
            if cost_tot is not None:
                try:
                    res["cost_per_acre"] = round(float(cost_tot) / max(1e-6, area), 2)
                except Exception:
                    res["cost_per_acre"] = None
            # margin: compute from pf if revenue present
            margin = pf.get("margin_percent")
            if margin is not None:
                res["profit_margin_pct"] = round(float(margin), 2)
    except Exception:
        pass

    # irrigation liters per acre — try to fetch from irrigation schedule if available (best-effort)
    try:
        from app.services.farmer.irrigation_service import get_irrigation_schedule
        sch = get_irrigation_schedule(unit_id)
        if sch and sch.get("events"):
            total_liters = sum(e.get("liters", 0) for e in sch["events"])
            area = float(sch.get("area_acre", 1.0) or 1.0)
            res["irrigation_l_per_acre"] = round(total_liters / max(1e-6, area), 2)
    except Exception:
        pass

    return res


# ---- Public: benchmark a unit against peers ----
def benchmark_unit_against_peers(unit_id: str) -> Dict[str, Any]:
    """
    Returns:
      - unit_metrics
      - peer_distributions (median + list)
      - percentile_ranks for each metric
      - narrative summary with actionable notes
    """
    unit_metrics = _compute_unit_metrics(unit_id)
    dists = _gather_peer_distributions()

    percentiles = {}
    medians = {}
    notes = []

    for metric in ["yield_q_per_acre", "cost_per_acre", "profit_margin_pct", "irrigation_l_per_acre"]:
        unit_val = unit_metrics.get(metric)
        dist_vals = dists.get(metric, []) or []
        med_info = _median_and_percentile_list(dist_vals)
        medians[metric] = med_info["median"]
        if unit_val is None:
            percentiles[metric] = None
        else:
            pr = _percentile_rank(unit_val, dist_vals) if dist_vals else None
            percentiles[metric] = pr

            # add simple narrative notes
            if metric == "yield_q_per_acre" and pr is not None:
                if pr < 25:
                    notes.append("Yield is in the lower quartile vs peers — review seed rate, fertilizer application and pest risks.")
                elif pr < 50:
                    notes.append("Yield is below median — look for marginal gains in inputs and operations.")
                elif pr < 75:
                    notes.append("Yield is above median — good performance; consider market/price optimization.")
                else:
                    notes.append("Yield is in top quartile — best-in-class performance.")

            if metric == "cost_per_acre" and pr is not None:
                # lower cost == better rank (so invert interpretation)
                if pr < 25:
                    notes.append("Cost per acre is relatively high vs peers — check input prices and labor efficiency.")
                elif pr > 75:
                    notes.append("Cost per acre is low vs peers — good cost control, confirm yield not suffering.")

            if metric == "profit_margin_pct" and pr is not None:
                if pr < 40:
                    notes.append("Profit margin is low relative to peers — consider price discovery or cost cutting.")
                else:
                    notes.append("Profit margin looks healthy vs peers.")

    summary = {
        "unit_id": unit_id,
        "unit_metrics": unit_metrics,
        "peer_medians": medians,
        "percentile_ranks": percentiles,
        "notes": notes,
        "peer_count": len(dists.get("yield_q_per_acre", [])),
        "generated_at": datetime.utcnow().isoformat()
    }

    return summary


# ---- Fleet-level benchmarking (aggregate report) ----
def fleet_benchmark_summary() -> Dict[str, Any]:
    """
    Aggregate across all local units and compare to peers:
      - compute local averages and percentiles vs peer medians
    """
    # compute local unit metrics
    local_metrics = []
    for uid in list(_unit_store.keys()):
        m = _compute_unit_metrics(uid)
        # skip if metrics mostly None
        local_metrics.append(m)

    # aggregate local stats (median per metric)
    def _agg_metric(key):
        vals = [v[key] for v in local_metrics if v.get(key) is not None]
        return round(statistics.median(vals), 3) if vals else None

    local_summary = {
        "local_median_yield_q_per_acre": _agg_metric("yield_q_per_acre"),
        "local_median_cost_per_acre": _agg_metric("cost_per_acre"),
        "local_median_profit_margin_pct": _agg_metric("profit_margin_pct"),
        "units_evaluated": len(local_metrics)
    }

    peer_dists = _gather_peer_distributions()
    peer_medians = {k: statistics.median(v) if v else None for k, v in peer_dists.items()}

    return {
        "local_summary": local_summary,
        "peer_medians": peer_medians,
        "generated_at": datetime.utcnow().isoformat()
    }
