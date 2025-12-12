# backend/app/api/marketplace/logistics.py

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any

from app.services.marketplace.logistics_service import (
    register_transporter,
    get_transporter,
    list_transporters,
    register_vehicle,
    list_vehicles,
    get_vehicle,
    estimate_transport,
    create_transport_job,
    assign_vehicle_to_job,
    update_job_status,
    add_tracking_ping,
    get_tracking,
    get_job,
    list_jobs_for_transporter,
    list_jobs_for_requester,
    cancel_job,
    weekly_transport_summary
)

router = APIRouter()


# Payloads
class TransporterPayload(BaseModel):
    transporter_id: Optional[str] = None
    name: str
    contact: Optional[str] = None


class VehiclePayload(BaseModel):
    transporter_id: str
    vehicle_no: str
    capacity_kg: float
    vehicle_type: Optional[str] = "truck"
    metadata: Optional[Dict[str, Any]] = None


class EstimatePayload(BaseModel):
    pickup_lat: float
    pickup_lon: float
    drop_lat: float
    drop_lon: float
    per_km_rate: Optional[float] = None
    base_fee: Optional[float] = None


class CreateJobPayload(BaseModel):
    order_id: Optional[str] = None
    requested_by: str
    pickup: Dict[str, Any]
    drop: Dict[str, Any]
    scheduled_date_iso: Optional[str] = None
    required_capacity_kg: Optional[float] = None
    preferred_vehicle_type: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class AssignPayload(BaseModel):
    job_id: str
    vehicle_id: str


class StatusPayload(BaseModel):
    job_id: str
    status: str
    note: Optional[str] = None


class TrackingPayload(BaseModel):
    job_id: str
    lat: float
    lon: float
    note: Optional[str] = None


# Endpoints
@router.post("/market/logistics/transporter/register")
def api_register_transporter(req: TransporterPayload):
    return register_transporter(req.transporter_id, req.name, contact=req.contact)


@router.get("/market/logistics/transporter/{transporter_id}")
def api_get_transporter(transporter_id: str):
    res = get_transporter(transporter_id)
    if not res:
        raise HTTPException(status_code=404, detail="transporter_not_found")
    return res


@router.get("/market/logistics/transporters")
def api_list_transporters():
    return {"transporters": list_transporters()}


@router.post("/market/logistics/vehicle/register")
def api_register_vehicle(req: VehiclePayload):
    return register_vehicle(req.transporter_id, req.vehicle_no, req.capacity_kg, vehicle_type=req.vehicle_type, metadata=req.metadata)


@router.get("/market/logistics/vehicles")
def api_list_vehicles(transporter_id: Optional[str] = None, active_only: Optional[bool] = True):
    return {"vehicles": list_vehicles(transporter_id=transporter_id, active_only=bool(active_only))}


@router.get("/market/logistics/vehicle/{vehicle_id}")
def api_get_vehicle(vehicle_id: str):
    res = get_vehicle(vehicle_id)
    if not res:
        raise HTTPException(status_code=404, detail="vehicle_not_found")
    return res


@router.post("/market/logistics/estimate")
def api_estimate(req: EstimatePayload):
    return estimate_transport(req.pickup_lat, req.pickup_lon, req.drop_lat, req.drop_lon, per_km_rate=req.per_km_rate, base_fee=req.base_fee)


@router.post("/market/logistics/job/create")
def api_create_job(req: CreateJobPayload):
    return create_transport_job(req.order_id, req.requested_by, req.pickup, req.drop, scheduled_date_iso=req.scheduled_date_iso, required_capacity_kg=req.required_capacity_kg, preferred_vehicle_type=req.preferred_vehicle_type, metadata=req.metadata)


@router.post("/market/logistics/job/assign")
def api_assign(req: AssignPayload):
    res = assign_vehicle_to_job(req.job_id, req.vehicle_id)
    if "error" in res:
        raise HTTPException(status_code=400, detail=res["error"])
    return res


@router.post("/market/logistics/job/status")
def api_update_status(req: StatusPayload):
    res = update_job_status(req.job_id, req.status, note=req.note)
    if "error" in res:
        raise HTTPException(status_code=400, detail=res["error"])
    return res


@router.post("/market/logistics/job/track")
def api_add_tracking(req: TrackingPayload):
    res = add_tracking_ping(req.job_id, req.lat, req.lon, note=req.note)
    if "error" in res:
        raise HTTPException(status_code=400, detail=res["error"])
    return res


@router.get("/market/logistics/job/{job_id}/tracking")
def api_get_tracking(job_id: str):
    return get_tracking(job_id)


@router.get("/market/logistics/job/{job_id}")
def api_get_job(job_id: str):
    res = get_job(job_id)
    if not res:
        raise HTTPException(status_code=404, detail="job_not_found")
    return res


@router.get("/market/logistics/jobs/transporter/{transporter_id}")
def api_jobs_for_transporter(transporter_id: str, status: Optional[str] = None):
    return {"jobs": list_jobs_for_transporter(transporter_id, status_filter=status)}


@router.get("/market/logistics/jobs/requester/{requester_id}")
def api_jobs_for_requester(requester_id: str):
    return {"jobs": list_jobs_for_requester(requester_id)}


@router.post("/market/logistics/job/{job_id}/cancel")
def api_cancel_job(job_id: str, reason: Optional[str] = None):
    res = cancel_job(job_id, reason=reason)
    if "error" in res:
        raise HTTPException(status_code=400, detail=res["error"])
    return res


@router.get("/market/logistics/summary/weekly")
def api_weekly_summary(transporter_id: Optional[str] = None, weeks: Optional[int] = 8):
    return weekly_transport_summary(transporter_id=transporter_id, weeks=weeks or 8)
