"""
API Routes — Cluster Intelligence (Farmer POV)

Endpoints:
 - POST /farmer/cluster/analyze        -> run cluster analysis (supply neighbors or lat/lon)
 - GET  /farmer/cluster/{cluster_id}   -> get specific analysis
 - GET  /farmer/cluster                -> list previous analyses
"""

from fastapi import APIRouter, HTTPException, Body, Query
from typing import Optional, List, Dict, Any

from app.services.farmer import cluster_intelligence_service as svc

router = APIRouter()


@router.post("/farmer/cluster/analyze")
async def api_analyze_cluster(
    unit_id: Optional[str] = Query(None),
    lat: Optional[float] = Query(None),
    lon: Optional[float] = Query(None),
    radius_km: float = Query(5.0),
    payload: Optional[Dict[str, Any]] = Body(None)
):
    """
    Body may include:
      neighbors: list of neighbor dicts with optional keys:
        unit_id, lat, lon, ndvi, canopy, yield_est, pest_risk, disease_risk, soil_moisture
      notes: optional text

    Example request body:
    {
      "neighbors": [
         {"unit_id":"u1","lat":12.1,"lon":77.1,"ndvi":0.6,"pest_risk":0.2},
         ...
      ],
      "notes": "ad-hoc cluster run"
    }
    """
    neighbors = None
    notes = None
    if payload:
        neighbors = payload.get("neighbors")
        notes = payload.get("notes")

    res = svc.analyze_cluster(unit_id=unit_id, lat=lat, lon=lon, radius_km=radius_km, neighbors=neighbors, notes=notes)
    return res


@router.get("/farmer/cluster/{cluster_id}")
def api_get_cluster(cluster_id: str):
    rec = svc.get_cluster(cluster_id)
    if not rec:
        raise HTTPException(status_code=404, detail="cluster_not_found")
    return rec


@router.get("/farmer/cluster")
def api_list_clusters():
    return svc.list_clusters()
