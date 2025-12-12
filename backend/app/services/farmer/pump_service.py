# backend/app/services/farmer/pump_service.py

"""
Water Pump Efficiency Model (Feature 306)

- Register pumps (farmer-owned equipment of type 'pump')
- Record usage sessions (start_iso, end_iso, duration_hours, flow_rate_lph, volume_l, energy_kwh, fuel_liters)
- Compute observed efficiency metrics:
    - liters_per_kwh (L/kWh)
    - liters_per_lfuel (L/Lfuel)
    - kwh_per_1000_liters
- Estimate energy or fuel needed to pump a given volume using historical or rated efficiency
- Predict maintenance due based on runtime_hours thresholds
- Provide pump overview with health estimates and simple maintenance scheduling hints
"""

from datetime import datetime, timedelta
from threading import Lock
from typing import Dict, Any, List, Optional
import uuid
import statistics
import math

# best-effort integrations (do not crash if modules absent)
try:
    from app.services.farmer.water_service import get_tank
except Exception:
    get_tank = None

try:
    from app.services.farmer.equipment_service import get_equipment
except Exception:
    get_equipment = None

try:
    from app.services.farmer.finance_service import query_ledger
except Exception:
    query_ledger = None

_lock = Lock()

# stores
_pumps: Dict[str, Dict[str, Any]] = {}          # pump_id -> pump record
_pumps_by_farmer: Dict[str, List[str]] = {}     # farmer_id -> [pump_ids]
_usage_logs: Dict[str, List[Dict[str, Any]]] = {}  # pump_id -> [usage_record]

# defaults
DEFAULT_MAINTENANCE_HOURS = 250.0  # run-hours before recommended service
DEFAULT_EFFICIENCY_LPKWH = 2000.0  # liters per kWh (very rough default for centrifugal pumps at low head)
DEFAULT_FUEL_EFFICIENCY_LL = 10000.0  # liters per liter-fuel (if diesel engine pump) - placeholder

def _now_iso() -> str:
    return datetime.utcnow().isoformat()

def _uid(prefix: str = "pump") -> str:
    return f"{prefix}_{uuid.uuid4()}"

# -------------------------
# Pump registry (CRUD)
# -------------------------
def add_pump(
    farmer_id: str,
    name: str,
    equipment_id: Optional[str] = None,
    pump_type: Optional[str] = "centrifugal",  # centrifugal, submersible, diesel, solar
    rated_flow_lph: Optional[float] = None,
    rated_power_kw: Optional[float] = None,
    rated_head_m: Optional[float] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    pid = _uid("pump")
    rec = {
        "pump_id": pid,
        "farmer_id": farmer_id,
        "name": name,
        "equipment_id": equipment_id,
        "pump_type": pump_type,
        "rated_flow_lph": float(rated_flow_lph) if rated_flow_lph is not None else None,
        "rated_power_kw": float(rated_power_kw) if rated_power_kw is not None else None,
        "rated_head_m": float(rated_head_m) if rated_head_m is not None else None,
        "created_at": _now_iso(),
        "updated_at": None,
        "metadata": metadata or {},
    }
    with _lock:
        _pumps[pid] = rec
        _pumps_by_farmer.setdefault(farmer_id, []).append(pid)
    return rec

def get_pump(pump_id: str) -> Dict[str, Any]:
    with _lock:
        rec = _pumps.get(pump_id)
        return rec.copy() if rec else {}

def list_pumps(farmer_id: str) -> List[Dict[str, Any]]:
    with _lock:
        ids = _pumps_by_farmer.get(farmer_id, [])
        return [ _pumps[i].copy() for i in ids ]

def update_pump(pump_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
    with _lock:
        rec = _pumps.get(pump_id)
        if not rec:
            return {"error": "not_found"}
        # coerce numeric fields
        for k in ("rated_flow_lph","rated_power_kw","rated_head_m"):
            if k in updates and updates[k] is not None:
                try:
                    updates[k] = float(updates[k])
                except Exception:
                    pass
        rec.update(updates)
        rec["updated_at"] = _now_iso()
        _pumps[pump_id] = rec
        return rec.copy()

def delete_pump(pump_id: str) -> Dict[str, Any]:
    with _lock:
        rec = _pumps.pop(pump_id, None)
        if not rec:
            return {"error": "not_found"}
        farmer_id = rec.get("farmer_id")
        if farmer_id and farmer_id in _pumps_by_farmer:
            _pumps_by_farmer[farmer_id] = [i for i in _pumps_by_farmer[farmer_id] if i != pump_id]
        _usage_logs.pop(pump_id, None)
        return {"status": "deleted", "pump_id": pump_id}

# -------------------------
# Usage recording
# -------------------------
def record_usage(
    pump_id: str,
    start_iso: Optional[str] = None,
    end_iso: Optional[str] = None,
    duration_hours: Optional[float] = None,
    flow_rate_lph: Optional[float] = None,
    volume_liters: Optional[float] = None,
    energy_kwh: Optional[float] = None,
    fuel_liters: Optional[float] = None,
    note: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Record a usage session.
    - Provide either start_iso & end_iso OR duration_hours.
    - Provide either flow_rate_lph OR volume_liters. If flow_rate provided with duration, volume is computed.
    - energy_kwh and/or fuel_liters are optionally provided; otherwise efficiency derived metrics will be missing/estimated.
    """
    with _lock:
        pump = _pumps.get(pump_id)
        if not pump:
            return {"error": "pump_not_found"}

    # parse timestamps
    now = datetime.utcnow()
    start_dt = None
    end_dt = None
    if start_iso:
        try:
            start_dt = datetime.fromisoformat(start_iso)
        except Exception:
            start_dt = now
    if end_iso:
        try:
            end_dt = datetime.fromisoformat(end_iso)
        except Exception:
            end_dt = None

    if not start_dt and duration_hours is None:
        start_dt = now

    if duration_hours is not None:
        try:
            dur = float(duration_hours)
        except Exception:
            dur = None
        if dur is not None and (end_dt is None):
            end_dt = (start_dt + timedelta(hours=dur)) if start_dt else (now + timedelta(hours=dur))
    elif start_dt and end_dt is None:
        end_dt = now

    duration_h = None
    try:
        duration_h = (end_dt - start_dt).total_seconds() / 3600.0 if start_dt and end_dt else None
    except Exception:
        duration_h = duration_hours

    # compute volume if not provided
    vol_l = None
    if volume_liters is not None:
        try:
            vol_l = float(volume_liters)
        except Exception:
            vol_l = None
    elif flow_rate_lph is not None and duration_h is not None:
        try:
            vol_l = float(flow_rate_lph) * duration_h
        except Exception:
            vol_l = None

    # store record
    rec = {
        "usage_id": _uid("u"),
        "pump_id": pump_id,
        "start_iso": start_dt.isoformat() if start_dt else None,
        "end_iso": end_dt.isoformat() if end_dt else None,
        "duration_hours": round(duration_h, 3) if duration_h is not None else None,
        "flow_rate_lph": float(flow_rate_lph) if flow_rate_lph is not None else None,
        "volume_liters": round(vol_l, 3) if vol_l is not None else None,
        "energy_kwh": float(energy_kwh) if energy_kwh is not None else None,
        "fuel_liters": float(fuel_liters) if fuel_liters is not None else None,
        "note": note or "",
        "metadata": metadata or {},
        "recorded_at": _now_iso()
    }

    with _lock:
        _usage_logs.setdefault(pump_id, []).append(rec)

    return rec

def list_usage(pump_id: str, limit: int = 200) -> List[Dict[str, Any]]:
    with _lock:
        items = list(_usage_logs.get(pump_id, []))
    items_sorted = sorted(items, key=lambda r: r.get("recorded_at",""), reverse=True)[:limit]
    return items_sorted

# -------------------------
# Efficiency calculations
# -------------------------
def compute_efficiency_metrics(pump_id: str) -> Dict[str, Any]:
    """
    Compute observed efficiency metrics from usage logs:
      - liters_per_kwh (L/kWh) using records where energy_kwh is provided
      - liters_per_fuel (L/Lfuel) using records where fuel_liters provided
      - avg_flow_lph, avg_duration_hours, total_runtime_hours
    Falls back to rated spec if insufficient observations.
    """
    with _lock:
        pump = _pumps.get(pump_id)
        if not pump:
            return {"error": "pump_not_found"}
        usages = list(_usage_logs.get(pump_id, []))

    if not usages:
        # fallback: use rated specs
        rated_flow = pump.get("rated_flow_lph")
        rated_power = pump.get("rated_power_kw")
        if rated_flow and rated_power:
            # assume 1 hour run
            lpkwh = rated_flow / (rated_power * 1.0) if rated_power > 0 else DEFAULT_EFFICIENCY_LPKWH
        else:
            lpkwh = DEFAULT_EFFICIENCY_LPKWH
        return {
            "pump_id": pump_id,
            "lpkwh": round(lpkwh,2),
            "lplfuel": None,
            "avg_flow_lph": rated_flow,
            "avg_duration_hours": None,
            "total_runtime_hours": 0.0,
            "n_records": 0
        }

    # compute liters per kwh from usage records with both volume and energy
    lpkwh_vals = []
    lplfuel_vals = []
    flow_vals = []
    dur_vals = []
    total_runtime = 0.0
    for u in usages:
        vol = u.get("volume_liters")
        e = u.get("energy_kwh")
        f = u.get("fuel_liters")
        dur = u.get("duration_hours")
        fr = u.get("flow_rate_lph")
        if vol is not None and e is not None and e > 0:
            lpkwh_vals.append(vol / e)
        if vol is not None and f is not None and f > 0:
            lplfuel_vals.append(vol / f)
        if fr is not None:
            flow_vals.append(fr)
        if dur is not None:
            dur_vals.append(dur)
            total_runtime += dur

    lpkwh = round(statistics.mean(lpkwh_vals), 2) if lpkwh_vals else (None)
    lplfuel = round(statistics.mean(lplfuel_vals), 2) if lplfuel_vals else (None)
    avg_flow = round(statistics.mean(flow_vals),2) if flow_vals else pump.get("rated_flow_lph")
    avg_dur = round(statistics.mean(dur_vals),3) if dur_vals else None

    # if no observed L/kWh, attempt to estimate using rated specs (if rated_power present)
    if lpkwh is None:
        rated_flow = pump.get("rated_flow_lph")
        rated_power = pump.get("rated_power_kw")
        if rated_flow and rated_power:
            # assume pump runs at rated power to deliver rated flow
            lpkwh = round(float(rated_flow) / (float(rated_power) * 1.0), 2)
        else:
            lpkwh = round(DEFAULT_EFFICIENCY_LPKWH, 2)

    return {
        "pump_id": pump_id,
        "lpkwh": lpkwh,
        "lplfuel": lplfuel,
        "avg_flow_lph": avg_flow,
        "avg_duration_hours": avg_dur,
        "total_runtime_hours": round(total_runtime,3),
        "n_records": len(usages)
    }

# -------------------------
# Energy / fuel estimation helpers
# -------------------------
def estimate_energy_for_volume(
    pump_id: str,
    target_volume_liters: float,
    use: str = "electric",   # "electric" or "fuel"
    head_m: Optional[float] = None,
    apply_efficiency_correction: bool = True
) -> Dict[str, Any]:
    """
    Estimate energy (kWh) or fuel (liters) required to pump `target_volume_liters`.
    Uses observed pump efficiency (lpkwh) or fallback defaults. Optionally accounts for head correction.
    head_m: if provided, we apply a simplistic head penalty: efficiency falls with higher head (linear approx).
    """
    with _lock:
        pump = _pumps.get(pump_id)
        if not pump:
            return {"error": "pump_not_found"}

    metrics = compute_efficiency_metrics(pump_id)
    lpkwh = metrics.get("lpkwh") or DEFAULT_EFFICIENCY_LPKWH
    lplfuel = metrics.get("lplfuel") or DEFAULT_FUEL_EFFICIENCY_LL

    # head correction: assume efficiency degrades by 3% per 10m head over rated_head_m
    correction = 1.0
    if apply_efficiency_correction and head_m is not None:
        rated_head = pump.get("rated_head_m")
        if rated_head is not None and rated_head > 0:
            delta = float(head_m) - float(rated_head)
            # degrade by 0.03 per 10 m (0.003 per m)
            correction = max(0.4, 1.0 - (0.003 * delta)) if delta > 0 else min(1.2, 1.0 - (0.001 * delta))
        else:
            # apply conservative penalty with head
            correction = max(0.5, 1.0 - (0.002 * float(head_m)))

    if use == "electric":
        effective_lpkwh = float(lpkwh) * correction
        # energy_kwh = target_volume_liters / lpkwh
        est_kwh = float(target_volume_liters) / effective_lpkwh if effective_lpkwh > 0 else None
        return {
            "pump_id": pump_id,
            "target_volume_liters": target_volume_liters,
            "estimated_kwh": round(est_kwh,3) if est_kwh is not None else None,
            "effective_lpkwh": round(effective_lpkwh,3),
            "head_correction": round(correction,3),
        }
    else:
        # fuel
        effective_lpl = float(lplfuel) * correction
        est_fuel_l = float(target_volume_liters) / effective_lpl if effective_lpl > 0 else None
        return {
            "pump_id": pump_id,
            "target_volume_liters": target_volume_liters,
            "estimated_fuel_liters": round(est_fuel_l,3) if est_fuel_l is not None else None,
            "effective_lplfuel": round(effective_lpl,3),
            "head_correction": round(correction,3),
        }

# -------------------------
# Maintenance prediction & health
# -------------------------
def predict_maintenance_due(pump_id: str, maintenance_interval_hours: Optional[float] = None) -> Dict[str, Any]:
    """
    Predict if maintenance is due based on accumulated runtime hours.
    maintenance_interval_hours: override default (e.g., 250h)
    """
    with _lock:
        pump = _pumps.get(pump_id)
        if not pump:
            return {"error": "pump_not_found"}
        usages = list(_usage_logs.get(pump_id, []))

    total_hours = 0.0
    for u in usages:
        h = u.get("duration_hours")
        if h:
            total_hours += float(h)
    interval = float(maintenance_interval_hours) if maintenance_interval_hours is not None else DEFAULT_MAINTENANCE_HOURS
    hours_to_service = max(0.0, interval - total_hours)
    due = total_hours >= interval
    # naive health score: 100 -> new, reduces with accumulated hours (linear)
    health = max(20.0, round(max(0.0, 100.0 - (total_hours / interval) * 80.0), 2))
    return {
        "pump_id": pump_id,
        "total_runtime_hours": round(total_hours,3),
        "maintenance_interval_hours": interval,
        "hours_to_service": round(hours_to_service,3),
        "due": due,
        "health_score": health
    }

# -------------------------
# Pump overview (aggregate)
# -------------------------
def pump_overview(farmer_id: str) -> Dict[str, Any]:
    with _lock:
        pump_ids = _pumps_by_farmer.get(farmer_id, [])
    overview = []
    for pid in pump_ids:
        p = get_pump(pid)
        eff = compute_efficiency_metrics(pid)
        maint = predict_maintenance_due(pid)
        # attach equipment record if available
        equipment = None
        try:
            if p.get("equipment_id") and get_equipment:
                equipment = get_equipment(p.get("equipment_id"))
        except Exception:
            equipment = None
        overview.append({
            "pump": p,
            "efficiency": eff,
            "maintenance": maint,
            "equipment": equipment
        })
    return {"farmer_id": farmer_id, "count": len(overview), "pumps": overview, "generated_at": _now_iso()}
