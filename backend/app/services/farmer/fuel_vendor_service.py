# backend/app/services/farmer/fuel_vendor_service.py

from datetime import datetime, timedelta
from threading import Lock
from typing import Dict, Any, List, Optional

# Reuse existing fuel logs from fuel_analytics_service
from app.services.farmer.fuel_analytics_service import _fuel_logs
from app.services.farmer.operator_behavior_service import compute_operator_behavior


# ---------------------------------------------------------
# In-memory vendor metadata store
# ---------------------------------------------------------

_fuel_vendor_store: Dict[str, Dict[str, Any]] = {}      # vendor_id -> vendor_info
_vendor_lock = Lock()


def add_fuel_vendor(vendor_id: str, name: str, location: Optional[str] = None) -> Dict[str, Any]:
    """
    Register a fuel vendor.
    """
    data = {
        "vendor_id": vendor_id,
        "name": name,
        "location": location,
        "created_at": datetime.utcnow().isoformat()
    }
    with _vendor_lock:
        _fuel_vendor_store[vendor_id] = data
    return data


def list_fuel_vendors() -> Dict[str, Any]:
    with _vendor_lock:
        return {"count": len(_fuel_vendor_store), "vendors": list(_fuel_vendor_store.values())}

def log_fuel_with_vendor(
    equipment_id: str,
    liters: float,
    cost: float,
    vendor_id: str,
    operator_id: Optional[str] = None,
    timestamp: Optional[str] = None
):
    """
    Adds a vendor-aware fuel log.
    """

    entry = {
        "equipment_id": equipment_id,
        "liters": liters,
        "cost": cost,
        "vendor_id": vendor_id,
        "operator_id": operator_id,
        "timestamp": timestamp or datetime.utcnow().isoformat()
    }
    _fuel_logs.append(entry)
    return entry

def analyze_vendor_for_equipment(
    equipment_id: str,
    lookback_days: int = 90
) -> Dict[str, Any]:
    """
    Computes vendor performance for a single equipment:
      - avg price/liter
      - volatility (std-like)
      - operator bias toward certain vendors
      - cost savings if switching to cheapest vendor
    """

    cutoff = datetime.utcnow() - timedelta(days=lookback_days)

    # gather logs for this equipment
    logs = [
        e for e in _fuel_logs
        if e.get("equipment_id") == equipment_id
        and e.get("vendor_id") is not None
        and datetime.fromisoformat(e["timestamp"]) >= cutoff
    ]

    if not logs:
        return {
            "equipment_id": equipment_id,
            "status": "no_vendor_data",
            "vendors": []
        }

    vendor_stats: Dict[str, Dict[str, Any]] = {}
    for e in logs:
        vid = e["vendor_id"]
        liters = max(0.001, abs(e["liters"]))
        price_per_liter = e["cost"] / liters

        v = vendor_stats.setdefault(vid, {
            "vendor_id": vid,
            "fuel_events": 0,
            "total_liters": 0.0,
            "total_cost": 0.0,
            "prices": [],
            "operators": {}
        })

        v["fuel_events"] += 1
        v["total_liters"] += liters
        v["total_cost"] += e["cost"]
        v["prices"].append(price_per_liter)

        op = e.get("operator_id")
        if op:
            v["operators"][op] = v["operators"].get(op, 0) + liters

    # calculate vendor metrics
    vendor_list = []
    for vid, v in vendor_stats.items():
        avg_price = v["total_cost"] / max(0.001, v["total_liters"])
        min_price = min(v["prices"])
        max_price = max(v["prices"])
        volatility = max_price - min_price  # simple spread

        # operator influence: find who uses this vendor most
        op_influence = None
        if v["operators"]:
            op_influence = sorted(v["operators"].items(), key=lambda x: x[1], reverse=True)[0]

        vendor_list.append({
            "vendor_id": vid,
            "avg_price_liter": round(avg_price, 2),
            "min_price": round(min_price, 2),
            "max_price": round(max_price, 2),
            "volatility": round(volatility, 2),
            "events": v["fuel_events"],
            "top_operator": op_influence
        })

    vendor_list.sort(key=lambda x: x["avg_price_liter"])

    # savings if switching to best vendor
    cheapest_price = vendor_list[0]["avg_price_liter"]
    total_spent = sum(e["cost"] for e in logs)
    total_liters = sum(max(0.001, abs(e["liters"])) for e in logs)
    current_price = total_spent / max(0.001, total_liters)

    monthly_savings = (current_price - cheapest_price) * total_liters
    monthly_savings = round(max(0, monthly_savings), 2)

    return {
        "equipment_id": equipment_id,
        "vendors": vendor_list,
        "current_avg_price": round(current_price, 2),
        "cheapest_vendor_id": vendor_list[0]["vendor_id"],
        "monthly_savings_if_switch": monthly_savings,
        "generated_at": datetime.utcnow().isoformat()
    }

def fleet_vendor_comparison(
    lookback_days: int = 90
) -> Dict[str, Any]:
    """
    Ranks vendors across entire fleet.
    """

    # gather all vendor logs
    cutoff = datetime.utcnow() - timedelta(days=lookback_days)
    logs = [
        e for e in _fuel_logs
        if e.get("vendor_id") is not None
        and datetime.fromisoformat(e["timestamp"]) >= cutoff
    ]

    vendor_stats = {}
    for e in logs:
        vid = e["vendor_id"]
        liters = max(0.001, abs(e["liters"]))
        price = e["cost"] / liters

        v = vendor_stats.setdefault(vid, {
            "vendor_id": vid,
            "total_liters": 0.0,
            "total_cost": 0.0,
            "prices": [],
        })

        v["total_liters"] += liters
        v["total_cost"] += e["cost"]
        v["prices"].append(price)

    vendor_list = []
    for vid, v in vendor_stats.items():
        avg_price = v["total_cost"] / max(0.001, v["total_liters"])
        min_price = min(v["prices"])
        max_price = max(v["prices"])
        volatility = max_price - min_price

        vendor_list.append({
            "vendor_id": vid,
            "avg_price_liter": round(avg_price, 2),
            "min_price": round(min_price, 2),
            "max_price": round(max_price, 2),
            "volatility": round(volatility, 2),
            "total_liters": round(v["total_liters"], 2),
        })

    vendor_list.sort(key=lambda x: x["avg_price_liter"])

    return {
        "lookback_days": lookback_days,
        "ranking": vendor_list,
        "generated_at": datetime.utcnow().isoformat()
    }
