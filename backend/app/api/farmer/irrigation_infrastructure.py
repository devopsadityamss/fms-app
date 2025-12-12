from fastapi import APIRouter
from app.services.farmer.irrigation_infrastructure_service import (
    register_channel, list_channels,
    register_flow_meter, list_flow_meters,
    log_flow_reading, list_flow_logs,
    estimate_leakage, get_channels_needing_inspection,
    irrigation_infra_summary
)

router = APIRouter()

# CHANNELS
@router.post("/irrigation/infra/channel")
def api_register_channel(payload: dict):
    return register_channel(**payload)

@router.get("/irrigation/infra/{unit_id}/channels")
def api_list_channels(unit_id: str):
    return list_channels(unit_id)


# FLOW METERS
@router.post("/irrigation/infra/meter")
def api_register_meter(payload: dict):
    return register_flow_meter(**payload)

@router.get("/irrigation/infra/channel/{channel_id}/meters")
def api_list_meters(channel_id: str):
    return list_flow_meters(channel_id)


# FLOW LOGS
@router.post("/irrigation/infra/meter/{meter_id}/log")
def api_log_flow(meter_id: str, payload: dict):
    return log_flow_reading(meter_id, payload["flow_lps"])

@router.get("/irrigation/infra/meter/{meter_id}/logs")
def api_list_logs(meter_id: str):
    return list_flow_logs(meter_id)


# LEAKAGE + INSPECTION
@router.get("/irrigation/infra/channel/{channel_id}/leakage")
def api_leakage(channel_id: str):
    return estimate_leakage(channel_id)

@router.get("/irrigation/infra/{unit_id}/inspection")
def api_inspection(unit_id: str):
    return get_channels_needing_inspection(unit_id)


# SUMMARY
@router.get("/irrigation/infra/{unit_id}/summary")
def api_infra_summary(unit_id: str):
    return irrigation_infra_summary(unit_id)
