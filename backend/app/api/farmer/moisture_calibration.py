# backend/app/api/farmer/moisture_calibration.py

from fastapi import APIRouter, Body, HTTPException, Query
from typing import Dict, Any, List, Optional

from app.services.farmer.moisture_calibration_service import (
    ingest_sensor_reading,
    list_sensor_readings,
    create_calibration_profile,
    get_profile,
    get_profile_for_sensor,
    list_profiles,
    delete_profile,
    map_sensor_to_lot,
    get_mapped_lot,
    train_profile_for_sensor,
    train_profile_from_samples,
    calibrated_timeseries_for_sensor,
    calibrated_timeseries_for_lot,
    calibration_summary_for_sensor,
    pair_lab_with_sensor_samples
)

router = APIRouter()


@router.post("/moisture/sensor/{sensor_id}/ingest")
def api_ingest_sensor(sensor_id: str, payload: Dict[str, Any] = Body(...)):
    """
    payload: { timestamp_iso (optional), raw_moisture_pct, metadata (optional) }
    """
    if "raw_moisture_pct" not in payload:
        raise HTTPException(status_code=400, detail="missing raw_moisture_pct")
    return ingest_sensor_reading(sensor_id, payload.get("timestamp_iso"), payload["raw_moisture_pct"], metadata=payload.get("metadata"))


@router.get("/moisture/sensor/{sensor_id}/readings")
def api_list_readings(sensor_id: str, limit: int = Query(1000)):
    return list_sensor_readings(sensor_id, limit=limit)


@router.post("/moisture/sensor/{sensor_id}/profile")
def api_create_profile(sensor_id: str, payload: Dict[str, Any] = Body(None)):
    """
    optional payload: { a, b, samples: [{raw, lab, ts}, ...] }
    """
    a = payload.get("a") if payload else 1.0
    b = payload.get("b") if payload else 0.0
    samples = payload.get("samples") if payload else None
    return create_calibration_profile(sensor_id, a=a, b=b, samples=samples)


@router.get("/moisture/profile/{profile_id}")
def api_get_profile(profile_id: str):
    p = get_profile(profile_id)
    if not p:
        raise HTTPException(status_code=404, detail="profile_not_found")
    return p

@router.get("/moisture/profile/by-sensor/{sensor_id}")
def api_get_profile_for_sensor(sensor_id: str):
    p = get_profile_for_sensor(sensor_id)
    return p or {}


@router.get("/moisture/profiles")
def api_list_profiles():
    return {"count": len(list_profiles()), "profiles": list_profiles()}


@router.delete("/moisture/profile/{profile_id}")
def api_delete_profile(profile_id: str):
    return delete_profile(profile_id)


@router.post("/moisture/sensor/{sensor_id}/map-to-lot")
def api_map_sensor_to_lot(sensor_id: str, payload: Dict[str, Any] = Body(...)):
    lot_id = payload.get("lot_id")
    if not lot_id:
        raise HTTPException(status_code=400, detail="missing lot_id")
    return map_sensor_to_lot(sensor_id, lot_id)


@router.get("/moisture/sensor/{sensor_id}/mapped-lot")
def api_get_mapped_lot(sensor_id: str):
    return {"sensor_id": sensor_id, "lot_id": get_mapped_lot(sensor_id)}


@router.post("/moisture/sensor/{sensor_id}/train")
def api_train_profile(sensor_id: str, payload: Dict[str, Any] = Body(...)):
    """
    payload: { samples: [{ raw: float, lab: float, ts (optional) }, ...] }
    """
    samples = payload.get("samples")
    if not samples:
        raise HTTPException(status_code=400, detail="missing samples")
    res = train_profile_for_sensor(sensor_id, samples)
    if res.get("error"):
        raise HTTPException(status_code=400, detail=res)
    return res

@router.post("/moisture/profile/{profile_id}/train")
def api_train_profile_id(profile_id: str, payload: Dict[str, Any] = Body(...)):
    samples = payload.get("samples")
    if not samples:
        raise HTTPException(status_code=400, detail="missing samples")
    res = train_profile_from_samples(profile_id, samples)
    if res.get("error"):
        raise HTTPException(status_code=400, detail=res)
    return res


@router.get("/moisture/sensor/{sensor_id}/calibrated-series")
def api_calibrated_series_sensor(sensor_id: str, limit: int = Query(1000)):
    return calibrated_timeseries_for_sensor(sensor_id, limit=limit)


@router.get("/moisture/lot/{lot_id}/calibrated-series")
def api_calibrated_series_lot(lot_id: str):
    return calibrated_timeseries_for_lot(lot_id)


@router.get("/moisture/sensor/{sensor_id}/summary")
def api_calibration_summary(sensor_id: str):
    return calibration_summary_for_sensor(sensor_id)


@router.post("/moisture/sensor/{sensor_id}/pair-lab")
def api_pair_lab(sensor_id: str, payload: Dict[str, Any] = Body(...)):
    """
    payload: { lab_samples: [{ ts: iso, lab_moisture_pct }, ...], max_seconds_delta (optional) }
    Returns paired samples {lab, sensor_reading}
    """
    samples = payload.get("lab_samples")
    if not samples:
        raise HTTPException(status_code=400, detail="missing lab_samples")
    max_seconds_delta = payload.get("max_seconds_delta", 3600)
    pairs = pair_lab_with_sensor_samples(sensor_id, samples, max_seconds_delta)
    return {"sensor_id": sensor_id, "pairs": pairs}
