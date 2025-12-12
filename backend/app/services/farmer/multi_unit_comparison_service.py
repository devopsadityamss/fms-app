"""
Multi-Unit Comparison Engine (stub-ready)
-----------------------------------------

Compares multiple farmer units across key indicators.

Inputs (supplied manually for now):
 - units: list of dicts, each may contain:
     unit_id
     yield_kg
     ndvi
     canopy
     pest_risk
     disease_risk
     water_usage_liters
     profit_estimate
     growth_delta
     custom metrics (optional)

Outputs:
 - normalized comparison scores (0–1)
 - ranking by metric
 - aggregate insights ("Unit 3 is highest yield", etc.)
 - in-memory record for dashboard usage

Later integration:
 - pull actual metrics from other modules automatically.
"""

from typing import Dict, Any, Optional, List
from datetime import datetime
import uuid


_comp_store: Dict[str, Dict[str, Any]] = {}


def _new_id() -> str:
    return str(uuid.uuid4())


def _now() -> str:
    return datetime.utcnow().isoformat()


# -------------------------------------------------------------
# Normalization helpers
# -------------------------------------------------------------
def _normalize(values: List[Optional[float]]) -> List[Optional[float]]:
    """
    Normalize list of numbers into 0–1 scale.
    None stays None.
    """
    clean = [v for v in values if v is not None]
    if not clean:
        return [None for _ in values]

    mn, mx = min(clean), max(clean)
    if mx == mn:
        return [0.5 if v is not None else None for v in values]  # flat values

    return [(v - mn) / (mx - mn) if v is not None else None for v in values]


def _rank_desc(values: List[Optional[float]], unit_ids: List[str]) -> List[Dict[str, Any]]:
    """
    Ranks units from highest to lowest based on provided numeric values.
    None values sorted last.
    """
    pairs = list(zip(unit_ids, values))
    sorted_pairs = sorted(
        pairs,
        key=lambda x: (-x[1], x[0]) if x[1] is not None else (1, x[0])
    )
    return [{"unit_id": u, "score": s} for (u, s) in sorted_pairs]


# -------------------------------------------------------------
# MAIN Comparison Logic
# -------------------------------------------------------------
def compare_units(units: List[Dict[str, Any]], notes: Optional[str] = None) -> Dict[str, Any]:
    comp_id = _new_id()

    # Extract metrics
    unit_ids = [u.get("unit_id") for u in units]

    yield_vals = [u.get("yield_kg") for u in units]
    ndvi_vals = [u.get("ndvi") for u in units]
    canopy_vals = [u.get("canopy") for u in units]
    pest_vals = [u.get("pest_risk") for u in units]
    disease_vals = [u.get("disease_risk") for u in units]
    water_vals = [u.get("water_usage_liters") for u in units]
    profit_vals = [u.get("profit_estimate") for u in units]
    growth_vals = [u.get("growth_delta") for u in units]

    # Normalize metrics
    norm = {
        "yield_norm": _normalize(yield_vals),
        "ndvi_norm": _normalize(ndvi_vals),
        "canopy_norm": _normalize(canopy_vals),
        "pest_norm": _normalize(pest_vals),
        "disease_norm": _normalize(disease_vals),
        "water_norm": _normalize(water_vals),   # lower usage = better? adjust later
        "profit_norm": _normalize(profit_vals),
        "growth_norm": _normalize(growth_vals),
    }

    # Rankings
    rankings = {
        "yield_rank": _rank_desc(norm["yield_norm"], unit_ids),
        "profit_rank": _rank_desc(norm["profit_norm"], unit_ids),
        "ndvi_rank": _rank_desc(norm["ndvi_norm"], unit_ids),
    }

    # Insights (stub)
    insights = []
    top_yield = rankings["yield_rank"][0]
    insights.append(f"Highest expected yield: {top_yield['unit_id']}")

    top_profit = rankings["profit_rank"][0]
    insights.append(f"Most profitable projection: {top_profit['unit_id']}")

    top_ndvi = rankings["ndvi_rank"][0]
    insights.append(f"Best canopy/NDVI health: {top_ndvi['unit_id']}")

    record = {
        "id": comp_id,
        "created_at": _now(),
        "units_compared": len(units),
        "raw_inputs": units,
        "normalized_metrics": norm,
        "rankings": rankings,
        "insights": insights,
        "notes": notes,
    }

    _comp_store[comp_id] = record
    return record


def get_comparison(comp_id: str) -> Optional[Dict[str, Any]]:
    return _comp_store.get(comp_id)


def list_comparisons() -> Dict[str, Any]:
    return {"count": len(_comp_store), "items": list(_comp_store.values())}


def _clear_store():
    _comp_store.clear()
