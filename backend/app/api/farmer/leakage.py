# backend/app/api/farmer/leakage.py

from fastapi import APIRouter, Body, HTTPException, Query
from typing import Optional, Dict, Any

from app.services.farmer.leakage_service import (
    add_channel,
    get_channel,
    list_channels,
    update_channel,
    delete_channel,
    record_flow_reading,
    list_flow_readings,
    channel_summary,
    list_anomalies,
    unit_leakage_overview,
    compute_risk_score
)

router = APIRouter()


@router.post("/channel")
def api_add_channel(payload: Dict[str, Any] = Body(...)):
    required = ["unit_id", "name"]
    for r in required:
        if r not in payload:
            raise HTTPException(status_code=400, detail=f"missing {r}")
    return add_channel(payload["unit_id"], payload["name"], expected_flow_lph=payload.get("expected_flow_lph"), metadata=payload.get("metadata"))

@router.get("/channel/{channel_id}")
def api_get_channel(channel_id: str):
    res = get_channel(channel_id)
    if not res:
        raise HTTPException(status_code=404, detail="channel_not_found")
    return res

@router.get("/channels/{unit_id}")
def api_list_channels(unit_id: str):
    return list_channels(unit_id)

@router.put("/channel/{channel_id}")
def api_update_channel(channel_id: str, updates: Dict[str, Any] = Body(...)):
    res = update_channel(channel_id, updates)
    if res.get("error"):
        raise HTTPException(status_code=404, detail=res)
    return res

@router.delete("/channel/{channel_id}")
def api_delete_channel(channel_id: str):
    res = delete_channel(channel_id)
    if res.get("error"):
        raise HTTPException(status_code=404, detail=res)
    return res

@router.post("/channel/{channel_id}/reading")
def api_record_reading(channel_id: str, payload: Dict[str, Any] = Body(...)):
    res = record_flow_reading(
        channel_id=channel_id,
        timestamp_iso=payload.get("timestamp_iso"),
        flow_lph=payload.get("flow_lph"),
        liters=payload.get("liters"),
        sensor_id=payload.get("sensor_id"),
        metadata=payload.get("metadata")
    )
    if res.get("error"):
        raise HTTPException(status_code=404, detail=res)
    return res

@router.get("/channel/{channel_id}/readings")
def api_list_readings(channel_id: str, limit: int = Query(200)):
    return list_flow_readings(channel_id, limit=limit)

@router.get("/channel/{channel_id}/summary")
def api_channel_summary(channel_id: str):
    res = channel_summary(channel_id)
    if res.get("error"):
        raise HTTPException(status_code=404, detail=res)
    return res

@router.get("/channel/{channel_id}/anomalies")
def api_list_anomalies(channel_id: str, limit: int = Query(200)):
    return list_anomalies(channel_id, limit=limit)

@router.get("/channels/{unit_id}/overview")
def api_unit_overview(unit_id: str):
    return unit_leakage_overview(unit_id)

@router.get("/channel/{channel_id}/risk")
def api_channel_risk(channel_id: str):
    res = compute_risk_score(channel_id)
    if res.get("error"):
        raise HTTPException(status_code=404, detail=res)
    return res
