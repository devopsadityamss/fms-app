# backend/app/services/marketplace/logistics_service.py

from datetime import datetime, timedelta
from threading import Lock
from typing import Dict, Any, List, Optional
import uuid
import math

"""
Marketplace Logistics & Transport Booking (in-memory)

Key concepts:
 - transporters: transporter_id -> profile
 - vehicles: vehicle_id -> metadata (transporter_id, capacity_kg, vehicle_type)
 - transport_jobs: job_id -> job record (order_id, pickup, drop, status, assigned_vehicle, timestamps)
 - tracking: job_id -> list of {ts, lat, lon, note}
 - basic estimate: naive Haversine distance -> hours, price = base + per_km rate
"""

_lock = Lock()

_transporter_store: Dict[str, Dict[str, Any]] = {}
_vehicle_store: Dict[str, Dict[str, Any]] = {}
_job_store: Dict[str, Dict[str, Any]] = {}
_tracking_store: Dict[str, List[Dict[str, Any]]] = {}

# config
_DEFAULT_PER_KM_RATE = 5.0  # currency per km
_DEFAULT_BASE_FEE = 200.0   # base fee
_AVG_SPEED_KMPH = 35.0      # average speed estimate


def _now_iso():
    return datetime.utcnow().isoformat()


# -----------------------
# Transporter & Vehicle registry
# -----------------------
def register_transporter(transporter_id: Optional[str], name: str, contact: Optional[str] = None) -> Dict[str, Any]:
    pid = transporter_id or f"trans_{uuid.uuid4()}"
    rec = {"transporter_id": pid, "name": name, "contact": contact, "registered_at": _now_iso()}
    with _lock:
        _transporter_store[pid] = rec
    return rec


def get_transporter(transporter_id: str) -> Dict[str, Any]:
    return _transporter_store.get(transporter_id, {})


def list_transporters() -> List[Dict[str, Any]]:
    with _lock:
        return list(_transporter_store.values())


def register_vehicle(transporter_id: str, vehicle_no: str, capacity_kg: float, vehicle_type: Optional[str] = "truck", metadata: Optional[Dict[str,Any]] = None) -> Dict[str, Any]:
    vid = f"veh_{uuid.uuid4()}"
    rec = {
        "vehicle_id": vid,
        "transporter_id": transporter_id,
        "vehicle_no": vehicle_no,
        "capacity_kg": float(capacity_kg),
        "vehicle_type": vehicle_type,
        "metadata": metadata or {},
        "created_at": _now_iso(),
        "active": True
    }
    with _lock:
        _vehicle_store[vid] = rec
    return rec


def list_vehicles(transporter_id: Optional[str] = None, active_only: bool = True) -> List[Dict[str, Any]]:
    with _lock:
        items = list(_vehicle_store.values())
    if transporter_id:
        items = [v for v in items if v.get("transporter_id") == transporter_id]
    if active_only:
        items = [v for v in items if v.get("active", True)]
    return items


def get_vehicle(vehicle_id: str) -> Dict[str, Any]:
    return _vehicle_store.get(vehicle_id, {})


# -----------------------
# Utilities: distance, ETA, cost estimate (naive)
# -----------------------
def _haversine_km(lat1, lon1, lat2, lon2):
    # radius earth km
    R = 6371.0
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi/2.0)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlambda/2.0)**2
    c = 2*math.atan2(math.sqrt(a), math.sqrt(1-a))
    return R * c


def estimate_transport(pickup_lat: float, pickup_lon: float, drop_lat: float, drop_lon: float, per_km_rate: Optional[float] = None, base_fee: Optional[float] = None) -> Dict[str, Any]:
    per_km = per_km_rate if per_km_rate is not None else _DEFAULT_PER_KM_RATE
    base = base_fee if base_fee is not None else _DEFAULT_BASE_FEE
    dist_km = round(_haversine_km(pickup_lat, pickup_lon, drop_lat, drop_lon), 2)
    est_hours = round(dist_km / _AVG_SPEED_KMPH, 2) if _AVG_SPEED_KMPH > 0 else None
    price = round(base + (dist_km * per_km), 2)
    return {"distance_km": dist_km, "estimated_hours": est_hours, "estimated_price": price, "per_km": per_km, "base_fee": base}


# -----------------------
# Transport job lifecycle
# -----------------------
def create_transport_job(
    order_id: Optional[str],
    requested_by: str,  # marketplace or user id who requested
    pickup: Dict[str, Any],  # {lat, lon, address}
    drop: Dict[str, Any],    # {lat, lon, address}
    scheduled_date_iso: Optional[str] = None,
    required_capacity_kg: Optional[float] = None,
    preferred_vehicle_type: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    job_id = f"job_{uuid.uuid4()}"
    est = estimate_transport(pickup.get("lat"), pickup.get("lon"), drop.get("lat"), drop.get("lon"))
    rec = {
        "job_id": job_id,
        "order_id": order_id,
        "requested_by": requested_by,
        "pickup": pickup,
        "drop": drop,
        "scheduled_date_iso": scheduled_date_iso,
        "required_capacity_kg": required_capacity_kg,
        "preferred_vehicle_type": preferred_vehicle_type,
        "assigned_vehicle_id": None,
        "assigned_transporter_id": None,
        "status": "requested",  # requested -> assigned -> enroute -> picked_up -> delivered -> completed | cancelled
        "estimate": est,
        "price_estimate": est.get("estimated_price"),
        "metadata": metadata or {},
        "created_at": _now_iso(),
        "updated_at": _now_iso()
    }
    with _lock:
        _job_store[job_id] = rec
        _tracking_store[job_id] = []
    return rec


def assign_vehicle_to_job(job_id: str, vehicle_id: str) -> Dict[str, Any]:
    with _lock:
        job = _job_store.get(job_id)
        veh = _vehicle_store.get(vehicle_id)
        if not job:
            return {"error": "job_not_found"}
        if not veh:
            return {"error": "vehicle_not_found"}
        if job.get("status") in ["cancelled", "completed"]:
            return {"error": "invalid_job_status"}
        job["assigned_vehicle_id"] = vehicle_id
        job["assigned_transporter_id"] = veh.get("transporter_id")
        job["status"] = "assigned"
        job["updated_at"] = _now_iso()
        _job_store[job_id] = job
    return job


def update_job_status(job_id: str, status: str, note: Optional[str] = None) -> Dict[str, Any]:
    allowed = ["requested","assigned","enroute","picked_up","delivered","completed","cancelled"]
    if status not in allowed:
        return {"error": "invalid_status"}
    with _lock:
        job = _job_store.get(job_id)
        if not job:
            return {"error": "job_not_found"}
        job["status"] = status
        job["updated_at"] = _now_iso()
        if note:
            job.setdefault("notes", []).append({"ts": _now_iso(), "note": note})
        _job_store[job_id] = job
    return job


def add_tracking_ping(job_id: str, lat: float, lon: float, note: Optional[str] = None) -> Dict[str, Any]:
    with _lock:
        if job_id not in _job_store:
            return {"error": "job_not_found"}
        ping = {"ts": _now_iso(), "lat": float(lat), "lon": float(lon), "note": note}
        _tracking_store.setdefault(job_id, []).append(ping)
    return {"status": "ok", "ping": ping}


def get_tracking(job_id: str) -> Dict[str, Any]:
    with _lock:
        return {"job_id": job_id, "tracking": list(_tracking_store.get(job_id, []))}


def get_job(job_id: str) -> Dict[str, Any]:
    return _job_store.get(job_id, {})


def list_jobs_for_transporter(transporter_id: str, status_filter: Optional[str] = None) -> List[Dict[str, Any]]:
    with _lock:
        items = [j for j in _job_store.values() if j.get("assigned_transporter_id") == transporter_id]
    if status_filter:
        items = [i for i in items if i.get("status") == status_filter]
    return items


def list_jobs_for_requester(requester_id: str) -> List[Dict[str, Any]]:
    with _lock:
        return [j for j in _job_store.values() if j.get("requested_by") == requester_id]


def cancel_job(job_id: str, reason: Optional[str] = None) -> Dict[str, Any]:
    with _lock:
        job = _job_store.get(job_id)
        if not job:
            return {"error": "job_not_found"}
        job["status"] = "cancelled"
        job["cancel_reason"] = reason
        job["updated_at"] = _now_iso()
        _job_store[job_id] = job
    return job


# -----------------------
# Summaries / reports
# -----------------------
def weekly_transport_summary(transporter_id: Optional[str] = None, weeks: int = 8) -> Dict[str, Any]:
    end = datetime.utcnow().date()
    start = end - timedelta(weeks=weeks)
    summary = {}
    with _lock:
        for j in _job_store.values():
            if transporter_id and j.get("assigned_transporter_id") != transporter_id:
                continue
            try:
                created = datetime.fromisoformat(j.get("created_at")).date()
            except Exception:
                continue
            if created < start:
                continue
            wk = created.isocalendar()[1]
            summary.setdefault(wk, {"jobs": 0, "km": 0.0})
            summary[wk]["jobs"] += 1
            # accumulate distance if estimate present
            summary[wk]["km"] += float(j.get("estimate", {}).get("distance_km", 0.0))
    return {"weeks": weeks, "summary": summary}
