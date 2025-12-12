# backend/app/services/farmer/irrigation_audit_service.py

"""
Irrigation Audit Log Engine
---------------------------
Records every irrigation-related action:
 - irrigation events
 - moisture updates
 - weather updates
 - system recommendations
 - overrides (farmer decisions)
 - deviation alerts
 - leakage alerts (from infrastructure)

Provides:
 - chronological audit trail
 - audit filtering
 - audit summaries
"""

from datetime import datetime
from typing import Dict, Any, List, Optional
import uuid

_audit_logs: Dict[str, Dict[str, Any]] = {}
_logs_by_unit: Dict[str, List[str]] = {}


def _now():
    return datetime.utcnow().isoformat()


# --------------------------------------------------------------------
# GENERIC AUDIT RECORD
# --------------------------------------------------------------------
def _add_audit_record(
    unit_id: str,
    event_type: str,
    message: str,
    metadata: Optional[Dict[str, Any]] = None
):
    aid = f"audit_{uuid.uuid4()}"
    rec = {
        "audit_id": aid,
        "unit_id": unit_id,
        "type": event_type,    # irrigation_log, moisture_update, weather_update, recommendation, override, deviation, leakage_alert, etc.
        "message": message,
        "metadata": metadata or {},
        "timestamp": _now()
    }
    _audit_logs[aid] = rec
    _logs_by_unit.setdefault(unit_id, []).append(aid)
    return rec


# --------------------------------------------------------------------
# SPECIFIC AUDIT HELPERS
# --------------------------------------------------------------------
def audit_irrigation_event(unit_id: str, method: str, liters: float):
    return _add_audit_record(
        unit_id,
        "irrigation_log",
        f"Irrigation performed using {method}, water used: {liters} liters.",
        {"method": method, "liters": liters}
    )


def audit_moisture_update(unit_id: str, moisture: float):
    return _add_audit_record(
        unit_id,
        "moisture_update",
        f"Soil moisture updated to {moisture}%.",
        {"moisture_pct": moisture}
    )


def audit_weather_update(unit_id: str, rainfall: float, et0: float):
    return _add_audit_record(
        unit_id,
        "weather_update",
        f"Weather updated: rainfall={rainfall} mm, ET0={et0}.",
        {"rainfall_mm": rainfall, "et0": et0}
    )


def audit_system_recommendation(unit_id: str, rec: Dict[str, Any]):
    return _add_audit_record(
        unit_id,
        "recommendation",
        "System generated irrigation recommendation.",
        {"recommendation": rec}
    )


def audit_override(unit_id: str, reason: str, details: Optional[Dict[str, Any]] = None):
    return _add_audit_record(
        unit_id,
        "override",
        f"Farmer override: {reason}",
        details
    )


def audit_deviation(unit_id: str, deviation_pct: float, status: str):
    return _add_audit_record(
        unit_id,
        "deviation",
        f"Water deviation detected: {deviation_pct}% ({status})",
        {"deviation_pct": deviation_pct, "status": status}
    )


def audit_leakage_alert(unit_id: str, channel_id: str, score: float):
    return _add_audit_record(
        unit_id,
        "leakage_alert",
        f"Leakage risk detected for channel {channel_id}: risk score {score}.",
        {"channel_id": channel_id, "risk_score": score}
    )


# --------------------------------------------------------------------
# LISTING + FILTERING + SUMMARY
# --------------------------------------------------------------------
def list_audit_logs(unit_id: str, types: Optional[List[str]] = None):
    ids = _logs_by_unit.get(unit_id, [])
    logs = [_audit_logs[i] for i in ids]

    if types:
        logs = [l for l in logs if l["type"] in types]

    logs = sorted(logs, key=lambda x: x["timestamp"])
    return {"unit_id": unit_id, "count": len(logs), "logs": logs}


def audit_summary(unit_id: str):
    logs = _logs_by_unit.get(unit_id, [])
    out = {}

    for aid in logs:
        t = _audit_logs[aid]["type"]
        out[t] = out.get(t, 0) + 1

    return {
        "unit_id": unit_id,
        "summary": out,
        "total": len(logs),
        "timestamp": _now()
    }
