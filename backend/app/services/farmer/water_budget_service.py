# backend/app/services/farmer/water_budget_service.py

"""
Water-Year Budgeting & Seasonal Water Balance Engine
----------------------------------------------------
Features:
 - Estimate full-season water demand
 - Compute available water from multiple sources
 - Apply recharge rates over time
 - Detect shortage windows
 - Compute budget health score
 - Provide seasonal summary
"""

from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
import math

from app.services.farmer.multi_source_irrigation_service import (
    list_water_sources
)

def _now():
    return datetime.utcnow().isoformat()


# ----------------------------------------------------------
# DEMAND CALCULATION (SEASONAL)
# ----------------------------------------------------------
def estimate_season_water_demand(
    crop: str,
    area_acres: float,
    days: int,
    avg_et0_mm: float = 4.0,
    kc: float = 1.0,
    expected_rain_mm: float = 250
):
    """
    Simple model:
      daily_need = et0 * kc (mm)
      annual_need_mm = daily_need * days
      subtract expected rainfall
      convert mm -> liters
    """

    area_m2 = area_acres * 4046.856

    gross_mm = avg_et0_mm * kc * days
    net_mm = max(0, gross_mm - expected_rain_mm)

    liters = net_mm * area_m2

    return {
        "days": days,
        "gross_mm": round(gross_mm, 2),
        "net_mm": round(net_mm, 2),
        "required_liters": round(liters, 2)
    }


# ----------------------------------------------------------
# AVAILABLE WATER (SOURCE + RECHARGE MODEL)
# ----------------------------------------------------------
def estimate_available_water(unit_id: str, days: int):
    """
    Models:
      - Available water = current available + recharge (days * rate)
      - Tank/canal types may have fixed availability
    """

    sources = list_water_sources(unit_id)
    total = 0.0
    detail = []

    for s in sources:
        base = s["available_liters"]
        recharge = s["recharge_rate_lph"] * 24 * days if s["recharge_rate_lph"] > 0 else 0

        amt = max(0, base + recharge)
        total += amt

        detail.append({
            "source_id": s["source_id"],
            "name": s["name"],
            "type": s["type"],
            "base": base,
            "recharge": recharge,
            "projected_available": round(amt, 2)
        })

    return {
        "total_available_liters": round(total, 2),
        "sources": detail
    }


# ----------------------------------------------------------
# SHORTAGE WINDOW DETECTION
# ----------------------------------------------------------
def detect_shortage_windows(required_liters: float, available_liters: float, days: int):
    """
    Rough rule:
      required_per_day = required / days
      available_per_day = available / days
    """

    req_pd = required_liters / days
    avail_pd = available_liters / days

    if avail_pd >= req_pd:
        return {
            "status": "no_shortage",
            "shortage_days": 0,
            "message": "Available water meets daily requirement."
        }

    deficit_pd = req_pd - avail_pd
    shortage_days = math.ceil(required_liters / avail_pd) if avail_pd > 0 else days

    return {
        "status": "shortage_expected",
        "daily_deficit_liters": round(deficit_pd, 2),
        "shortage_days_estimate": shortage_days,
        "message": "Shortage likely based on current availability and recharge."
    }


# ----------------------------------------------------------
# HEALTH SCORE
# ----------------------------------------------------------
def compute_water_budget_score(required_liters: float, available_liters: float):
    if required_liters <= 0:
        return 100
    ratio = available_liters / required_liters
    score = max(0, min(100, round(ratio * 100, 2)))
    return score


# ----------------------------------------------------------
# FULL SEASONAL SUMMARY
# ----------------------------------------------------------
def water_budget_summary(
    unit_id: str,
    crop: str,
    area_acres: float,
    season_days: int,
    avg_et0_mm: float,
    kc: float,
    expected_rain_mm: float = 250
):
    demand = estimate_season_water_demand(
        crop, area_acres, season_days, avg_et0_mm, kc, expected_rain_mm
    )

    available = estimate_available_water(unit_id, season_days)

    score = compute_water_budget_score(
        demand["required_liters"],
        available["total_available_liters"]
    )

    shortage = detect_shortage_windows(
        demand["required_liters"],
        available["total_available_liters"],
        season_days
    )

    return {
        "unit_id": unit_id,
        "season_days": season_days,
        "crop": crop,
        "demand": demand,
        "available_water": available,
        "water_budget_score": score,
        "shortage_analysis": shortage,
        "generated_at": _now()
    }
