"""
Cluster Intelligence Service (stub-ready)
-----------------------------------------

Purpose:
 - Provide aggregated, cluster-level insights derived from nearby units.
 - Basic operations:
     - register a cluster analysis request
     - run a stubbed analysis using available neighbor metrics
     - compute aggregates (avg NDVI, avg yield, pest/disease prevalence)
     - flag anomalies and simple recommendations (water, scouting, fertilizer)
 - Everything is in-memory for now. Replace neighbor discovery and metrics
   with real geospatial queries & models later.

Design notes:
 - The service expects input neighbor metadata (list of dicts) OR will run
   a very light-weight geographic lookup when geo info is provided.
 - Keep function signatures stable so ML/analytics can be swapped in later.
"""

from typing import Dict, Any, Optional, List
from datetime import datetime
import uuid
import math

# In-memory store: cluster_id -> record
_cluster_store: Dict[str, Dict[str, Any]] = {}

# -------------------------
# Utilities
# -------------------------
def _now() -> str:
    return datetime.utcnow().isoformat()

def _new_id() -> str:
    return str(uuid.uuid4())

def _haversine_km(lat1, lon1, lat2, lon2):
    """Return distance in kilometers between two lat/lon points (approx)."""
    # Edge-case safe
    try:
        R = 6371.0
        phi1 = math.radians(float(lat1))
        phi2 = math.radians(float(lat2))
        dphi = math.radians(float(lat2) - float(lat1))
        dlambda = math.radians(float(lon2) - float(lon1))

        a = math.sin(dphi/2.0)**2 + math.cos(phi1)*math.cos(phi2)*(math.sin(dlambda/2.0)**2)
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        return R * c
    except Exception:
        return None

# -------------------------
# Aggregation helpers
# -------------------------
def _aggregate_neighbors(neighbors: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    neighbors: list of dicts, each may contain:
      - unit_id, lat, lon, ndvi (0-1), canopy (0-1), yield_est (kg),
        pest_risk (0-1), disease_risk (0-1), soil_moisture (0-1)
    This returns averages and simple prevalence metrics.
    """
    if not neighbors:
        return {
            "count": 0,
            "avg_ndvi": None,
            "avg_canopy": None,
            "avg_yield": None,
            "avg_pest_risk": None,
            "avg_disease_risk": None,
            "avg_soil_moisture": None,
            "high_pest_pct": 0.0,
            "high_disease_pct": 0.0,
        }

    total_ndvi = total_canopy = total_yield = total_pest = total_disease = total_moisture = 0.0
    cnt_ndvi = cnt_canopy = cnt_yield = cnt_pest = cnt_disease = cnt_moisture = 0
    high_pest = 0
    high_disease = 0

    for n in neighbors:
        ndvi = n.get("ndvi")
        if ndvi is not None:
            total_ndvi += float(ndvi); cnt_ndvi += 1
        canopy = n.get("canopy")
        if canopy is not None:
            total_canopy += float(canopy); cnt_canopy += 1
        y = n.get("yield_est")
        if y is not None:
            total_yield += float(y); cnt_yield += 1
        pr = n.get("pest_risk")
        if pr is not None:
            total_pest += float(pr); cnt_pest += 1
            if pr > 0.6:
                high_pest += 1
        dr = n.get("disease_risk")
        if dr is not None:
            total_disease += float(dr); cnt_disease += 1
            if dr > 0.6:
                high_disease += 1
        sm = n.get("soil_moisture")
        if sm is not None:
            total_moisture += float(sm); cnt_moisture += 1

    count = len(neighbors)
    return {
        "count": count,
        "avg_ndvi": round(total_ndvi / cnt_ndvi, 3) if cnt_ndvi else None,
        "avg_canopy": round(total_canopy / cnt_canopy, 3) if cnt_canopy else None,
        "avg_yield": round(total_yield / cnt_yield, 2) if cnt_yield else None,
        "avg_pest_risk": round(total_pest / cnt_pest, 3) if cnt_pest else None,
        "avg_disease_risk": round(total_disease / cnt_disease, 3) if cnt_disease else None,
        "avg_soil_moisture": round(total_moisture / cnt_moisture, 3) if cnt_moisture else None,
        "high_pest_pct": round((high_pest / count) * 100.0, 1),
        "high_disease_pct": round((high_disease / count) * 100.0, 1),
    }

# -------------------------
# Simple anomaly detector (stub)
# -------------------------
def _detect_anomalies(aggregates: Dict[str, Any]) -> List[str]:
    out = []
    ndvi = aggregates.get("avg_ndvi")
    pest = aggregates.get("avg_pest_risk")
    disease = aggregates.get("avg_disease_risk")
    moisture = aggregates.get("avg_soil_moisture")

    if ndvi is not None and ndvi < 0.4:
        out.append("Cluster NDVI low — vegetation stress possible.")
    if pest is not None and pest > 0.6:
        out.append("Cluster has elevated pest risk.")
    if disease is not None and disease > 0.6:
        out.append("Cluster has elevated disease risk.")
    if moisture is not None and moisture < 0.25:
        out.append("Cluster soil moisture low — irrigation check recommended.")
    return out or ["No major anomalies detected."]

# -------------------------
# Public API: run cluster analysis
# -------------------------
def analyze_cluster(
    unit_id: Optional[str] = None,
    lat: Optional[float] = None,
    lon: Optional[float] = None,
    radius_km: float = 5.0,
    neighbors: Optional[List[Dict[str, Any]]] = None,
    notes: Optional[str] = None
) -> Dict[str, Any]:
    """
    If neighbors list is supplied, use it. Otherwise this stub cannot discover neighbors by geo —
    real implementation would query your unit registry / geo-index.
    """

    cluster_id = _new_id()
    used_neighbors = neighbors or []

    # If geo given and no explicit neighbors, we return empty (stub)
    # Real impl: lookup units within radius_km of lat/lon
    if not used_neighbors and lat is not None and lon is not None:
        # stub: emulate 0 neighbors found
        used_neighbors = []

    aggregates = _aggregate_neighbors(used_neighbors)
    anomalies = _detect_anomalies(aggregates)

    # Basic recommendations (stub)
    recs = []
    if aggregates.get("high_pest_pct", 0) > 20:
        recs.append("Area-level scouting recommended for pest hotspots.")
    if aggregates.get("avg_ndvi") is not None and aggregates["avg_ndvi"] < 0.45:
        recs.append("Investigate nutrient or water stress in the cluster.")
    if aggregates.get("avg_soil_moisture") is not None and aggregates["avg_soil_moisture"] < 0.3:
        recs.append("Consider irrigation adjustments across cluster.")

    record = {
        "id": cluster_id,
        "unit_id": unit_id,
        "center": {"lat": lat, "lon": lon},
        "radius_km": radius_km,
        "neighbors_used": len(used_neighbors),
        "aggregates": aggregates,
        "anomalies": anomalies,
        "recommendations": recs,
        "notes": notes,
        "created_at": _now(),
    }

    _cluster_store[cluster_id] = record
    return record

def get_cluster(cluster_id: str) -> Optional[Dict[str, Any]]:
    return _cluster_store.get(cluster_id)

def list_clusters() -> Dict[str, Any]:
    items = list(_cluster_store.values())
    return {"count": len(items), "items": items}

def _clear_store():
    _cluster_store.clear()
