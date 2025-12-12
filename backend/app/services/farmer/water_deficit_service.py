# backend/app/services/farmer/water_deficit_service.py

from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional

from app.services.farmer.irrigation_service import list_irrigation_logs, get_weather
from app.services.farmer.water_budget_service import estimate_season_water_demand


# In-memory store for deficit alerts
_water_deficit_alerts: Dict[str, List[Dict[str, Any]]] = {}


def _now():
    return datetime.utcnow().isoformat()


# ----------------------------------------------------------
# EXPECTED VS ACTUAL WATER MODEL
# ----------------------------------------------------------
def _expected_daily_mm(et0_mm: float, kc: float, rain_mm: float):
    net = max(0, et0_mm * kc - rain_mm)
    return float(net)


def _actual_daily_liters(unit_id: str, date_iso: str):
    logs = list_irrigation_logs(unit_id)
    total = 0.0
    for l in logs:
        if l["created_at"].startswith(date_iso):
            if l.get("water_used_liters"):
                total += l["water_used_liters"]
    return total


def _area_to_liters_per_mm(area_acres: float):
    # 1 mm = 1 liter / m2
    # acre → m2 conversion
    return area_acres * 4046.856  # liters per mm


# ----------------------------------------------------------
# CALCULATE DAILY DEFICIT
# ----------------------------------------------------------
def calculate_daily_deficit(
    unit_id: str,
    crop: str,
    area_acres: float,
    kc: float,
    date_iso: Optional[str] = None
):
    date_iso = date_iso or datetime.utcnow().date().isoformat()

    weather = get_weather(unit_id) or {"rainfall_mm": 0, "et0": 4}

    expected_mm = _expected_daily_mm(
        et0_mm=weather["et0"],
        kc=kc,
        rain_mm=weather["rainfall_mm"]
    )

    actual_liters = _actual_daily_liters(unit_id, date_iso)
    liters_per_mm = _area_to_liters_per_mm(area_acres)

    actual_mm = actual_liters / liters_per_mm if liters_per_mm else 0

    deficit_mm = expected_mm - actual_mm

    severity = "normal"
    if deficit_mm > 2:
        severity = "low"
    if deficit_mm > 4:
        severity = "medium"
    if deficit_mm > 8:
        severity = "high"
    if deficit_mm > 12:
        severity = "critical"

    record = {
        "unit_id": unit_id,
        "date": date_iso,
        "expected_mm": round(expected_mm, 2),
        "actual_mm": round(actual_mm, 2),
        "deficit_mm": round(deficit_mm, 2),
        "severity": severity,
        "generated_at": _now()
    }

    _water_deficit_alerts.setdefault(unit_id, []).append(record)

    return record


# ----------------------------------------------------------
# WEEKLY DEFICIT SUMMARY
# ----------------------------------------------------------
def weekly_water_deficit_summary(
    unit_id: str,
    crop: str,
    area_acres: float,
    kc: float,
    days: int = 7
):
    today = datetime.utcnow().date()
    results = []

    for i in range(days):
        date = today - timedelta(days=i)
        res = calculate_daily_deficit(
            unit_id=unit_id,
            crop=crop,
            area_acres=area_acres,
            kc=kc,
            date_iso=date.isoformat()
        )
        results.append(res)

    results = sorted(results, key=lambda x: x["date"])

    avg_deficit = sum(r["deficit_mm"] for r in results) / len(results)

    return {
        "unit_id": unit_id,
        "days_analyzed": days,
        "average_deficit_mm": round(avg_deficit, 2),
        "records": results,
        "generated_at": _now()
    }


# ----------------------------------------------------------
# LIST ALERTS
# ----------------------------------------------------------
def list_water_deficit_alerts(unit_id: str):
    return {
        "unit_id": unit_id,
        "alerts": _water_deficit_alerts.get(unit_id, [])
    }
