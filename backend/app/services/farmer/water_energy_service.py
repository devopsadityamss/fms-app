# backend/app/services/farmer/water_energy_service.py

"""
Water-Energy Mapping & Pump Energy Estimator (Feature 321)

Responsibilities:
- Maintain pump registry (optional) with power_kW, avg_flow_lph, efficiency
- Estimate energy (kWh) consumed for an irrigation event given:
    * flow_lph and duration_minutes  OR liters used
    * pump power_kW OR pump_rate_lph + pump_head & motor_efficiency (simple)
- Estimate cost using local tariff (per_kwh)
- Compute kWh per 1000 L (kWh/m3), cost per 1000 L
- Summarize energy usage per unit (aggregate irrigation logs)
- Best-effort integration with:
    - irrigation_service.list_irrigation_logs
    - pump_service (if present)
    - finance_service (to add cost entries) — optional
"""

from datetime import datetime
from threading import Lock
from typing import Dict, Any, List, Optional
import uuid
import math

# defensive imports
try:
    from app.services.farmer.irrigation_service import list_irrigation_logs
except Exception:
    # fallback: no-op
    list_irrigation_logs = lambda unit_id: []

try:
    from app.services.farmer.pump_service import get_pump
except Exception:
    get_pump = lambda pump_id: {}

try:
    from app.services.farmer.finance_service import add_ledger_entry
except Exception:
    add_ledger_entry = None

_lock = Lock()

_pumps: Dict[str, Dict[str, Any]] = {}          # pump_id -> { pump_id, name, power_kW, avg_flow_lph, efficiency, metadata }
_pumps_by_farmer: Dict[str, List[str]] = {}     # farmer_id -> [pump_ids]

# default electricity tariff (INR per kWh) — can be overridden per pump or per estimate call
DEFAULT_TARIFF_PER_KWH = 10.0

def _now_iso():
    return datetime.utcnow().isoformat()

def _uid(prefix="pump"):
    return f"{prefix}_{uuid.uuid4()}"

# -----------------------
# Pump registry (optional)
# -----------------------
def register_pump(
    farmer_id: str,
    name: str,
    power_kW: Optional[float] = None,
    avg_flow_lph: Optional[float] = None,
    efficiency_pct: Optional[float] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    power_kW: rated motor power in kW
    avg_flow_lph: typical flow in liters per hour for pump
    efficiency_pct: pump+motor efficiency (0..100)
    """
    pid = _uid("pump")
    rec = {
        "pump_id": pid,
        "farmer_id": farmer_id,
        "name": name,
        "power_kW": float(power_kW) if power_kW is not None else None,
        "avg_flow_lph": float(avg_flow_lph) if avg_flow_lph is not None else None,
        "efficiency_pct": float(efficiency_pct) if efficiency_pct is not None else None,
        "metadata": metadata or {},
        "created_at": _now_iso(),
        "updated_at": None
    }
    with _lock:
        _pumps[pid] = rec
        _pumps_by_farmer.setdefault(farmer_id, []).append(pid)
    return rec

def get_pump_record(pump_id: str) -> Dict[str, Any]:
    with _lock:
        return _pumps.get(pump_id, {}).copy()

def list_pumps(farmer_id: str) -> List[Dict[str, Any]]:
    with _lock:
        ids = _pumps_by_farmer.get(farmer_id, [])
        return [_pumps[i].copy() for i in ids]

def update_pump(pump_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
    with _lock:
        rec = _pumps.get(pump_id)
        if not rec:
            return {"error": "not_found"}
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
    return {"status": "deleted", "pump_id": pump_id}

# -----------------------
# Core estimators
# -----------------------
def estimate_energy_from_flow_and_duration(
    flow_lph: Optional[float] = None,
    duration_minutes: Optional[float] = None,
    liters: Optional[float] = None,
    pump_power_kW: Optional[float] = None,
    pump_efficiency_pct: Optional[float] = None,
    tariff_per_kwh: Optional[float] = None
) -> Dict[str, Any]:
    """
    Primary estimator:
    - If liters provided: use liters directly
    - Else require flow_lph and duration_minutes to compute liters
    - If pump_power_kW available: estimate kWh = power_kW * hours
    - Else fallback: infer power_kW from flow & assumed specific energy (heuristic)
    Returns:
      { liters, hours, estimated_kwh, tariff_per_kwh, estimated_cost, kwh_per_1000l }
    """

    # compute liters if necessary
    if liters is None:
        if flow_lph is None or duration_minutes is None:
            return {"error": "insufficient_flow_duration_info"}
        liters = float(flow_lph) * (float(duration_minutes) / 60.0)

    liters = float(liters)
    hours = None
    if duration_minutes is not None:
        hours = float(duration_minutes) / 60.0
    else:
        hours = max(0.0001, liters / (flow_lph or (liters / 0.0001)))  # fallback

    est_power_kW = None
    if pump_power_kW is not None:
        est_power_kW = float(pump_power_kW)
    else:
        # heuristic: assume 0.4 to 2.0 kW depending on flow
        # small pumps: <2000 L/h ~ 0.5 kW ; large pumps >10000 L/h ~ 2 kW
        if flow_lph is None:
            est_power_kW = 0.75
        else:
            f = float(flow_lph)
            est_power_kW = max(0.2, min(5.0, 0.3 + (f / 20000.0) * 2.0))

    # consider pump efficiency: if efficiency_pct provided, adjust electrical power needed
    if pump_efficiency_pct is not None and pump_efficiency_pct > 0:
        eff = float(pump_efficiency_pct) / 100.0
        # mechanical power needed remains same; electrical power = mechanical / eff.
        # Since we don't compute mechanical power explicitly here, we simply inflate est_power_kW by 1/eff
        try:
            est_power_kW = est_power_kW / max(0.01, eff)
        except Exception:
            pass

    est_kwh = round(est_power_kW * hours, 4)

    tariff = float(tariff_per_kwh) if tariff_per_kwh is not None else DEFAULT_TARIFF_PER_KWH
    cost = round(est_kwh * tariff, 2)

    # kWh per 1000 liters (m3)
    kwh_per_1000l = round((est_kwh / (liters / 1000.0)) if liters > 0 else None, 4)

    return {
        "liters": round(liters, 2),
        "hours": round(hours, 4),
        "estimated_power_kW": round(est_power_kW, 4),
        "estimated_kwh": est_kwh,
        "tariff_per_kwh": tariff,
        "estimated_cost": cost,
        "kwh_per_1000l": kwh_per_1000l,
        "generated_at": _now_iso()
    }

def estimate_energy_for_irrigation_log(
    irrigation_log: Dict[str, Any],
    pump_id: Optional[str] = None,
    tariff_per_kwh: Optional[float] = None
) -> Dict[str, Any]:
    """
    Given an irrigation log (as produced by irrigation_service.log_irrigation),
    estimate energy and optionally attach pump info.
    Expected irrigation_log keys: unit_id, method, duration_minutes, water_used_liters
    """
    flow_lph = None
    duration_minutes = irrigation_log.get("duration_minutes")
    liters = irrigation_log.get("water_used_liters")
    # if liters missing but duration and some flow metadata present in log.metadata, use it
    if liters is None and irrigation_log.get("metadata", {}).get("flow_lph") is not None and duration_minutes:
        flow_lph = irrigation_log["metadata"]["flow_lph"]

    pump_rec = None
    if pump_id:
        try:
            pump_rec = get_pump(pump_id) or get_pump_record(pump_id)
        except Exception:
            pump_rec = get_pump_record(pump_id)

    pump_power = None
    pump_eff = None
    if pump_rec:
        pump_power = pump_rec.get("power_kW")
        pump_eff = pump_rec.get("efficiency_pct")

    return estimate_energy_from_flow_and_duration(
        flow_lph=flow_lph,
        duration_minutes=duration_minutes,
        liters=liters,
        pump_power_kW=pump_power,
        pump_efficiency_pct=pump_eff,
        tariff_per_kwh=tariff_per_kwh
    )

# -----------------------
# Aggregations & summaries
# -----------------------
def summarize_unit_energy_usage(unit_id: str, days: int = 7, pump_id: Optional[str] = None, tariff_per_kwh: Optional[float] = None) -> Dict[str, Any]:
    """
    Aggregate last `days` irrigation logs for the unit and estimate energy & cost.
    """
    logs = list_irrigation_logs(unit_id) or []
    # filter by recent days (last N entries approximate)
    # Better if irrigation logs had dates — use created_at or timestamp if present
    total_liters = 0.0
    agg_kwh = 0.0
    agg_cost = 0.0
    details = []

    # naive: iterate all logs and include them (caller can provide filtered logs)
    for lg in logs:
        est = estimate_energy_for_irrigation_log(lg, pump_id=pump_id, tariff_per_kwh=tariff_per_kwh)
        total_liters += est.get("liters", 0) or 0
        agg_kwh += est.get("estimated_kwh", 0) or 0
        agg_cost += est.get("estimated_cost", 0) or 0
        details.append({"log": lg, "estimation": est})

    return {
        "unit_id": unit_id,
        "total_liters": round(total_liters, 2),
        "total_kwh": round(agg_kwh, 4),
        "total_cost": round(agg_cost, 2),
        "details_count": len(details),
        "details": details,
        "generated_at": _now_iso()
    }

# -----------------------
# Utility: record cost as ledger entry (best-effort)
# -----------------------
def record_energy_cost_to_ledger(
    farmer_id: str,
    unit_id: Optional[str],
    amount_inr: float,
    description: Optional[str] = None,
    tags: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    If finance_service.add_ledger_entry exists, add an expense line for irrigation energy.
    """
    if add_ledger_entry is None:
        return {"error": "finance_not_available"}
    entry = add_ledger_entry(
        farmer_id=farmer_id,
        unit_id=unit_id,
        entry_type="expense",
        category="irrigation_energy",
        amount=round(float(amount_inr), 2),
        currency="INR",
        date_iso=_now_iso(),
        description=description or "Irrigation energy expense",
        tags=tags or ["energy", "irrigation"],
        metadata={}
    )
    return entry
