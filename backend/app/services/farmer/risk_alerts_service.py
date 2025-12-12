# backend/app/services/farmer/risk_alerts_service.py

from datetime import datetime, timedelta
from threading import Lock
from typing import Dict, Any, List, Optional

# reuse unit & stage stores and input forecasting
from app.services.farmer.unit_service import _unit_store
from app.services.farmer.input_forecasting_service import forecast_inputs_for_unit

# simple in-memory alert store
_alerts_store: Dict[str, Dict[str, Any]] = {}
_alerts_lock = Lock()

# historical incident store (optional: can be used to learn patterns)
_incident_store: List[Dict[str, Any]] = []
_incident_lock = Lock()

# config thresholds (tuneable)
_DEFAULTS = {
    "drought_rain_threshold_mm_7d": 20.0,        # < this for last 7 days -> drought risk
    "flood_rain_threshold_24h": 80.0,            # > this in 24h -> flood risk
    "heat_temp_threshold_c": 38.0,               # > this -> heat stress
    "cold_temp_threshold_c": 6.0,                # < this -> cold stress
    "humidity_high_pct": 85.0,                   # high humidity favors fungal disease
    "seed_shortage_pct": 0.8,                    # if applied seed < 80% of forecast -> warning
    "nutrient_deficit_pct": 0.7,                 # if applied nutrient < 70% of expected -> deficiency
    "pesticide_missed_days": 14,                 # missed scheduled spray window (> days) -> pest risk
}


def _make_alert_id(unit_id: str, kind: str) -> str:
    return f"{unit_id}__{kind}__{int(datetime.utcnow().timestamp())}"


# --------------------------------------------------------------------------------
# Low-level: record & list alerts
# --------------------------------------------------------------------------------
def _record_alert(alert: Dict[str, Any]) -> Dict[str, Any]:
    aid = alert.get("alert_id") or _make_alert_id(alert.get("unit_id", "unknown"), alert.get("kind", "generic"))
    alert["alert_id"] = aid
    alert["created_at"] = datetime.utcnow().isoformat()
    alert["status"] = "open"
    with _alerts_lock:
        _alerts_store[aid] = alert
    return alert


def list_alerts(unit_id: Optional[str] = None, status: Optional[str] = None) -> Dict[str, Any]:
    with _alerts_lock:
        items = list(_alerts_store.values())
    if unit_id:
        items = [i for i in items if i.get("unit_id") == unit_id]
    if status:
        items = [i for i in items if i.get("status") == status]
    return {"count": len(items), "alerts": items}


def acknowledge_alert(alert_id: str, acknowledged_by: Optional[str] = None, note: Optional[str] = None) -> Dict[str, Any]:
    with _alerts_lock:
        rec = _alerts_store.get(alert_id)
        if not rec:
            return {"error": "alert_not_found"}
        rec["status"] = "acknowledged"
        rec["acknowledged_at"] = datetime.utcnow().isoformat()
        rec["acknowledged_by"] = acknowledged_by
        if note:
            rec["acknowledge_note"] = note
        _alerts_store[alert_id] = rec
    return rec


# --------------------------------------------------------------------------------
# Heuristic evaluators
# --------------------------------------------------------------------------------
def evaluate_weather_risks(
    unit_id: str,
    recent_weather: Dict[str, Any],
    lookback_weather: Optional[List[Dict[str, Any]]] = None,
    config: Optional[Dict[str, Any]] = None
) -> List[Dict[str, Any]]:
    """
    recent_weather: dictionary for current/last-24h e.g. {"rain_mm_24h": 5, "temp_c_max": 32, "temp_c_min": 22, "humidity_pct": 60}
    lookback_weather: list of daily dictionaries for last N days with keys: date_iso, rain_mm, temp_c_max, temp_c_min, humidity_pct
    Returns list of alert dicts (may be empty).
    """
    cfg = _DEFAULTS.copy()
    if config:
        cfg.update(config)

    alerts: List[Dict[str, Any]] = []

    # Flood risk: heavy rain in 24h
    rain24 = float(recent_weather.get("rain_mm_24h", 0) or 0)
    if rain24 >= cfg["flood_rain_threshold_24h"]:
        alerts.append({
            "unit_id": unit_id,
            "kind": "flood_risk",
            "severity": "high",
            "message": f"Heavy rainfall ({rain24} mm in 24h) — flood risk. Consider moving assets and draining fields.",
            "evidence": {"rain_mm_24h": rain24}
        })

    # Heat stress
    tmax = float(recent_weather.get("temp_c_max", 0) or 0)
    if tmax >= cfg["heat_temp_threshold_c"]:
        alerts.append({
            "unit_id": unit_id,
            "kind": "heat_stress",
            "severity": "medium" if tmax < cfg["heat_temp_threshold_c"] + 4 else "high",
            "message": f"High temperature observed (max {tmax}°C) — heat stress possible.",
            "evidence": {"temp_c_max": tmax}
        })

    # Cold stress
    tmin = float(recent_weather.get("temp_c_min", 999) or 999)
    if tmin <= cfg["cold_temp_threshold_c"]:
        alerts.append({
            "unit_id": unit_id,
            "kind": "cold_stress",
            "severity": "medium",
            "message": f"Low night temperature ({tmin}°C) — risk of cold damage.",
            "evidence": {"temp_c_min": tmin}
        })

    # Drought risk: compute last 7 days rainfall from lookback_weather if available
    if lookback_weather:
        last7 = lookback_weather[-7:] if len(lookback_weather) >= 7 else lookback_weather
        total7 = sum(float(d.get("rain_mm", 0) or 0) for d in last7)
        if total7 <= cfg["drought_rain_threshold_mm_7d"]:
            alerts.append({
                "unit_id": unit_id,
                "kind": "drought_risk",
                "severity": "high" if total7 < (cfg["drought_rain_threshold_mm_7d"] * 0.5) else "medium",
                "message": f"Low cumulative rainfall over last {len(last7)} days ({total7} mm) — drought risk. Check irrigation plan.",
                "evidence": {"rain_7d_mm": total7}
            })

    # High humidity → fungal disease risk (especially when temp moderate)
    hum = float(recent_weather.get("humidity_pct", 0) or 0)
    if hum >= cfg["humidity_high_pct"]:
        alerts.append({
            "unit_id": unit_id,
            "kind": "high_humidity_disease_risk",
            "severity": "medium",
            "message": f"High humidity ({hum}%) increases fungal disease risk. Check canopy and consider protective sprays.",
            "evidence": {"humidity_pct": hum}
        })

    return alerts


def evaluate_nutrient_and_input_risks(
    unit_id: str,
    inputs_snapshot: Optional[Dict[str, Any]] = None,
    expected_inputs: Optional[Dict[str, Any]] = None,
    config: Optional[Dict[str, Any]] = None
) -> List[Dict[str, Any]]:
    """
    Compare actual inputs (if recorded) vs expected from forecast_inputs_for_unit.
    inputs_snapshot: dict with 'seed_kg_applied' and 'fertilizer_applied' map and 'last_pesticide_date' ISO string etc.
    expected_inputs: if None, will call forecast_inputs_for_unit(unit_id)
    """
    cfg = _DEFAULTS.copy()
    if config:
        cfg.update(config)

    alerts: List[Dict[str, Any]] = []

    if expected_inputs is None:
        expected_inputs = forecast_inputs_for_unit(unit_id)

    totals = expected_inputs.get("total_inputs", {})

    # Seed shortage
    expected_seed = float(totals.get("seed_kg", 0) or 0)
    applied_seed = float((inputs_snapshot or {}).get("seed_kg_applied", 0) or 0)
    if expected_seed > 0 and applied_seed / expected_seed < cfg["seed_shortage_pct"]:
        alerts.append({
            "unit_id": unit_id,
            "kind": "seed_shortage",
            "severity": "high",
            "message": f"Applied seed ({applied_seed} kg) is less than recommended ({expected_seed} kg). Yield risk expected.",
            "evidence": {"applied_seed": applied_seed, "expected_seed": expected_seed}
        })

    # Nutrient deficiency (N,P,K)
    expected_fert = totals.get("fertilizer", {}) or {}
    applied_fert = (inputs_snapshot or {}).get("fertilizer_applied", {}) or {}
    for nut, expected_qty in expected_fert.items():
        expected_qty = float(expected_qty or 0)
        applied_qty = float(applied_fert.get(nut, 0) or 0)
        if expected_qty > 0 and (applied_qty / expected_qty) < cfg["nutrient_deficit_pct"]:
            alerts.append({
                "unit_id": unit_id,
                "kind": "nutrient_deficiency",
                "severity": "medium" if (applied_qty / expected_qty) >= 0.5 else "high",
                "message": f"Applied {nut} ({applied_qty} kg) is below recommended ({expected_qty} kg) — nutrient deficiency risk.",
                "evidence": {"nutrient": nut, "applied": applied_qty, "expected": expected_qty}
            })

    # Pesticide missed
    last_pest_iso = (inputs_snapshot or {}).get("last_pesticide_date")
    if last_pest_iso:
        try:
            last_date = datetime.fromisoformat(last_pest_iso)
            days_since = (datetime.utcnow() - last_date).days
            if days_since >= cfg["pesticide_missed_days"]:
                alerts.append({
                    "unit_id": unit_id,
                    "kind": "pesticide_missed",
                    "severity": "medium",
                    "message": f"Last pesticide spray was {days_since} days ago — miss interval; pest/disease risk increased.",
                    "evidence": {"days_since_last_pesticide": days_since, "last_pesticide_date": last_pest_iso}
                })
        except Exception:
            pass
    else:
        # no recorded spray — warn if crop stage expects sprays (best-effort)
        stage_template = (expected_inputs.get("stages") or [])
        expects_spray = any(s.get("pesticide_liters", 0) > 0 for s in stage_template)
        if expects_spray:
            alerts.append({
                "unit_id": unit_id,
                "kind": "pesticide_missing_record",
                "severity": "low",
                "message": "No pesticide application recorded; if scheduled, this increases pest risk.",
                "evidence": {}
            })

    return alerts


def evaluate_pest_disease_risks_from_weather_and_stage(
    unit_id: str,
    weather_now: Dict[str, Any],
    crop_stage_name: Optional[str] = None,
    historical_incidents: Optional[List[Dict[str, Any]]] = None
) -> List[Dict[str, Any]]:
    """
    Simple rules mapping common weather + stage combos to pest/disease risk.
    Example: high humidity + moderate temp during vegetative stage -> fungal risk.
    Returns alerts list.
    """
    alerts: List[Dict[str, Any]] = []
    hum = float(weather_now.get("humidity_pct", 0) or 0)
    tmin = float(weather_now.get("temp_c_min", 999) or 999)
    tmax = float(weather_now.get("temp_c_max", 0) or 0)

    # Example rule: rust/leaf spot (humidity>80 and temp 20–28 and stage vegetative/flowering)
    vegetative_stages = {"vegetative", "tillering", "vegetative_growth", "flowering", "fruiting"}
    if hum >= 80 and 20 <= tmax <= 28 and (crop_stage_name or "").lower() in vegetative_stages:
        alerts.append({
            "unit_id": unit_id,
            "kind": "fungal_disease_risk",
            "severity": "high",
            "message": f"Weather and stage indicate high fungal disease risk (humidity {hum}% and temp {tmax}°C).",
            "evidence": {"humidity_pct": hum, "temp_c_max": tmax, "stage": crop_stage_name}
        })

    # Example: stem borer risk in maize when temp high and humidity moderate
    if (crop_stage_name or "").lower() == "maize_reproductive" and tmax >= 30 and 50 <= hum <= 80:
        alerts.append({
            "unit_id": unit_id,
            "kind": "stem_borer_risk",
            "severity": "medium",
            "message": "Conditions favor stem borer activity; inspect plants.",
            "evidence": {"temp_c_max": tmax, "humidity_pct": hum}
        })

    # Check historical repeat incidents: if same pest occurred recently, raise alert higher
    if historical_incidents:
        recent_same = [h for h in historical_incidents if h.get("kind") and (h.get("kind").lower() in ["fungal", "blast", "bacterial"])]
        if recent_same:
            alerts.append({
                "unit_id": unit_id,
                "kind": "repeat_disease_risk",
                "severity": "high",
                "message": "Recent disease incidents recorded in this unit — elevated risk of recurrence.",
                "evidence": {"recent_count": len(recent_same)}
            })

    return alerts


# --------------------------------------------------------------------------------
# Public: evaluate risks for a unit (single call aggregator)
# --------------------------------------------------------------------------------
def evaluate_risks_for_unit(
    unit_id: str,
    weather_now: Optional[Dict[str, Any]] = None,
    lookback_weather: Optional[List[Dict[str, Any]]] = None,
    inputs_snapshot: Optional[Dict[str, Any]] = None,
    soil_quality: Optional[Dict[str, Any]] = None,
    crop_stage_name: Optional[str] = None,
    historical_incidents: Optional[List[Dict[str, Any]]] = None,
    config: Optional[Dict[str, Any]] = None,
    auto_record: bool = True
) -> Dict[str, Any]:
    """
    Drives all evaluators and returns recorded alerts (or empty list).
    - weather_now: dict with rain_mm_24h, temp_c_max, temp_c_min, humidity_pct
    - lookback_weather: list of daily weather dicts for last N days (for drought)
    - inputs_snapshot: {seed_kg_applied, fertilizer_applied: {N,P,K}, last_pesticide_date}
    - soil_quality: optional soil dict
    - crop_stage_name: optional current stage name
    """

    unit = _unit_store.get(unit_id)
    if not unit:
        return {"status": "unit_not_found", "unit_id": unit_id}

    # run sub-evaluators
    alerts: List[Dict[str, Any]] = []

    # weather-based
    if weather_now:
        alerts += evaluate_weather_risks(unit_id, weather_now, lookback_weather=lookback_weather, config=config)

    # nutrient/input based
    alerts += evaluate_nutrient_and_input_risks(unit_id, inputs_snapshot=inputs_snapshot, expected_inputs=None, config=config)

    # pest/disease combos
    if weather_now or crop_stage_name:
        alerts += evaluate_pest_disease_risks_from_weather_and_stage(unit_id, weather_now or {}, crop_stage_name, historical_incidents=historical_incidents)

    # soil-based nutrient deficiency checks (basic)
    if soil_quality:
        ph = float(soil_quality.get("ph", 7) or 7)
        if ph < 5.5 or ph > 8.5:
            alerts.append({
                "unit_id": unit_id,
                "kind": "soil_ph_issue",
                "severity": "medium",
                "message": f"Soil pH {ph} is outside ideal range (5.5-8.5). Nutrient availability may be affected.",
                "evidence": {"ph": ph}
            })

    # convert heuristics into formal alerts and optionally record them
    recorded = []
    for a in alerts:
        # enrich
        a_enriched = {
            "unit_id": a.get("unit_id"),
            "kind": a.get("kind"),
            "severity": a.get("severity", "low"),
            "message": a.get("message"),
            "evidence": a.get("evidence", {}),
            "suggested_actions": a.get("suggested_actions", [])
        }
        # add default suggested actions based on kind
        if not a_enriched["suggested_actions"]:
            if a_enriched["kind"] == "drought_risk":
                a_enriched["suggested_actions"] = ["Check irrigation schedule", "Prioritize water to this unit", "Mulch to reduce evaporation"]
            elif a_enriched["kind"] == "flood_risk":
                a_enriched["suggested_actions"] = ["Protect seedlings", "Create drainage paths", "Move movable assets"]
            elif "disease" in a_enriched["kind"] or "fungal" in a_enriched["kind"]:
                a_enriched["suggested_actions"] = ["Inspect canopy", "Apply recommended fungicide", "Reduce canopy humidity"]
            elif a_enriched["kind"] == "seed_shortage":
                a_enriched["suggested_actions"] = ["Top-up seed where possible", "Adjust sowing density"]
            elif a_enriched["kind"] == "nutrient_deficiency":
                a_enriched["suggested_actions"] = ["Top-dress fertilizer", "Soil test", "Foliar feed where appropriate"]
            elif a_enriched["kind"] == "pesticide_missed" or a_enriched["kind"] == "pesticide_missing_record":
                a_enriched["suggested_actions"] = ["Inspect for pests", "Schedule spray (targeted)"]
            else:
                a_enriched["suggested_actions"] = ["Inspect field", "Record observations"]

        if auto_record:
            rec = _record_alert(a_enriched)
            recorded.append(rec)
        else:
            recorded.append(a_enriched)

    return {"unit_id": unit_id, "alerts_count": len(recorded), "alerts": recorded, "generated_at": datetime.utcnow().isoformat()}


# --------------------------------------------------------------------------------
# Public: fleet-level evaluation
# --------------------------------------------------------------------------------
def evaluate_risks_for_fleet(
    weather_map: Optional[Dict[str, Dict[str, Any]]] = None,
    lookback_weather_map: Optional[Dict[str, List[Dict[str, Any]]]] = None,
    inputs_snapshots: Optional[Dict[str, Dict[str, Any]]] = None,
    soil_map: Optional[Dict[str, Dict[str, Any]]] = None,
    stage_map: Optional[Dict[str, str]] = None,
    historical_incidents_map: Optional[Dict[str, List[Dict[str, Any]]]] = None,
    config: Optional[Dict[str, Any]] = None,
    auto_record: bool = True
) -> Dict[str, Any]:
    """
    Evaluate risks for all units in the farm/portfolio.
    - weather_map: { unit_id: weather_now_dict }
    - inputs_snapshots: { unit_id: inputs_snapshot }
    returns aggregated alerts
    """
    results = []
    # iterate over all units
    for unit_id in list(_unit_store.keys()):
        weather_now = (weather_map or {}).get(unit_id)
        lookback_weather = (lookback_weather_map or {}).get(unit_id)
        inputs_snap = (inputs_snapshots or {}).get(unit_id)
        soil_q = (soil_map or {}).get(unit_id)
        stage = (stage_map or {}).get(unit_id)
        hist = (historical_incidents_map or {}).get(unit_id)
        r = evaluate_risks_for_unit(
            unit_id,
            weather_now=weather_now,
            lookback_weather=lookback_weather,
            inputs_snapshot=inputs_snap,
            soil_quality=soil_q,
            crop_stage_name=stage,
            historical_incidents=hist,
            config=config,
            auto_record=auto_record
        )
        results.append(r)
    return {"units_evaluated": len(results), "results": results, "generated_at": datetime.utcnow().isoformat()}


# --------------------------------------------------------------------------------
# Optional: record historical incident (for later learning / alerts history)
# --------------------------------------------------------------------------------
def record_incident(unit_id: str, kind: str, notes: Optional[str] = None) -> Dict[str, Any]:
    rec = {
        "incident_id": f"{unit_id}__{kind}__{int(datetime.utcnow().timestamp())}",
        "unit_id": unit_id,
        "kind": kind,
        "notes": notes,
        "recorded_at": datetime.utcnow().isoformat()
    }
    with _incident_lock:
        _incident_store.append(rec)
    return rec


def list_incidents(unit_id: Optional[str] = None) -> Dict[str, Any]:
    with _incident_lock:
        items = list(_incident_store)
    if unit_id:
        items = [i for i in items if i["unit_id"] == unit_id]
    return {"count": len(items), "incidents": items}
