# backend/app/services/farmer/irrigation_infrastructure_service.py

"""
Irrigation Infrastructure Intelligence Module
---------------------------------------------
Handles:
 - Channel registry (canal, open channel, pipe)
 - Flow meter registration
 - Flow readings (inlet/outlet)
 - Leakage rate estimation
 - Leakage risk scoring (0–100)
 - Inspection alerts
 - Infrastructure condition analytics
"""

from datetime import datetime
from typing import Dict, Any, Optional, List
import uuid
import math

# Stores (in-memory)
_channels: Dict[str, Dict[str, Any]] = {}            # channel_id -> channel record
_flow_meters: Dict[str, Dict[str, Any]] = {}         # meter_id -> meter record
_flow_logs: Dict[str, Dict[str, Any]] = {}           # reading_id -> reading record

_channels_by_unit: Dict[str, List[str]] = {}
_meters_by_channel: Dict[str, List[str]] = {}
_logs_by_meter: Dict[str, List[str]] = {}

# ---------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------
def _now():
    return datetime.utcnow().isoformat()


# ---------------------------------------------------------------------
# CHANNEL REGISTRATION
# ---------------------------------------------------------------------
def register_channel(
    unit_id: str,
    channel_name: str,
    length_m: float,
    width_cm: Optional[float] = None,
    material: Optional[str] = None,
    age_years: Optional[int] = None,
    design_flow_lps: Optional[float] = None
):
    cid = f"chn_{uuid.uuid4()}"
    rec = {
        "channel_id": cid,
        "unit_id": unit_id,
        "name": channel_name,
        "length_m": float(length_m),
        "width_cm": width_cm,
        "material": material or "unknown",
        "age_years": age_years,
        "design_flow_lps": design_flow_lps,
        "created_at": _now()
    }
    _channels[cid] = rec
    _channels_by_unit.setdefault(unit_id, []).append(cid)
    return rec


def list_channels(unit_id: str):
    return [_channels[c] for c in _channels_by_unit.get(unit_id, [])]


# ---------------------------------------------------------------------
# FLOW METER REGISTRATION
# ---------------------------------------------------------------------
def register_flow_meter(
    channel_id: str,
    meter_location: str,    # "upstream" or "downstream"
    description: Optional[str] = None
):
    mid = f"mtr_{uuid.uuid4()}"
    rec = {
        "meter_id": mid,
        "channel_id": channel_id,
        "location": meter_location,
        "description": description or "",
        "created_at": _now()
    }
    _flow_meters[mid] = rec
    _meters_by_channel.setdefault(channel_id, []).append(mid)
    return rec


def list_flow_meters(channel_id: str):
    return [_flow_meters[m] for m in _meters_by_channel.get(channel_id, [])]


# ---------------------------------------------------------------------
# FLOW LOGGING
# ---------------------------------------------------------------------
def log_flow_reading(
    meter_id: str,
    flow_lps: float
):
    rid = f"read_{uuid.uuid4()}"
    rec = {
        "reading_id": rid,
        "meter_id": meter_id,
        "flow_lps": float(flow_lps),
        "timestamp": _now()
    }
    _flow_logs[rid] = rec
    _logs_by_meter.setdefault(meter_id, []).append(rid)
    return rec


def list_flow_logs(meter_id: str):
    return [_flow_logs[r] for r in _logs_by_meter.get(meter_id, [])]


# ---------------------------------------------------------------------
# LEAKAGE RATE ESTIMATION
# ---------------------------------------------------------------------
def _latest_flow(meter_id: str):
    logs = list_flow_logs(meter_id)
    if not logs:
        return None
    logs = sorted(logs, key=lambda x: x["timestamp"], reverse=True)
    return logs[0]["flow_lps"]


def estimate_leakage(channel_id: str):
    meters = list_flow_meters(channel_id)
    up = down = None

    for m in meters:
        if m["location"] == "upstream":
            up = _latest_flow(m["meter_id"])
        elif m["location"] == "downstream":
            down = _latest_flow(m["meter_id"])

    if up is None or down is None:
        return {"status": "insufficient_data", "upstream": up, "downstream": down}

    if up <= 0:
        return {"status": "invalid_upstream_flow", "upstream": up, "downstream": down}

    leakage_fraction = max(0.0, (up - down) / up)
    leakage_pct = round(leakage_fraction * 100, 2)

    risk = 20 + leakage_pct
    age_factor = 1 + (max(0, _channels[channel_id].get("age_years", 0)) * 0.02)
    risk_score = min(100, round(risk * age_factor, 2))

    return {
        "status": "ok",
        "channel_id": channel_id,
        "upstream_lps": up,
        "downstream_lps": down,
        "leakage_pct": leakage_pct,
        "risk_score": risk_score,
        "timestamp": _now()
    }


# ---------------------------------------------------------------------
# INSPECTION & ALERTING
# ---------------------------------------------------------------------
def get_channels_needing_inspection(unit_id: str):
    results = []
    for cid in _channels_by_unit.get(unit_id, []):
        leak = estimate_leakage(cid)
        if leak.get("risk_score", 0) >= 40:
            results.append({
                "channel_id": cid,
                "risk_score": leak.get("risk_score"),
                "leakage_pct": leak.get("leakage_pct"),
                "severity": "high" if leak["risk_score"] >= 70 else "medium"
            })
    return {
        "unit_id": unit_id,
        "count": len(results),
        "items": results,
        "timestamp": _now()
    }


# ---------------------------------------------------------------------
# FULL SUMMARY
# ---------------------------------------------------------------------
def irrigation_infra_summary(unit_id: str):
    channels = list_channels(unit_id)
    out = []
    for c in channels:
        leak = estimate_leakage(c["channel_id"])
        out.append({
            **c,
            "leakage": leak
        })
    return {
        "unit_id": unit_id,
        "channels": out,
        "inspection_needed": get_channels_needing_inspection(unit_id),
        "timestamp": _now()
    }
