# backend/app/services/farmer/pricing_service.py
"""
Harvest Lot Quality-based Pricing Model (Feature 335)

- Stores simple in-memory market reference prices (per crop, per unit kg)
- Suggests lot-specific prices based on:
    * market_price
    * quality_score / grade (uses harvest_grading_service)
    * moisture / dockage penalties
    * lot age (freshness) adjustments
    * supply/demand multipliers (user-provided)
- Provides simulation helpers and bulk operations.
- Defensive: works if grading/traceability/finance services are missing.
"""

from datetime import datetime, timedelta
from threading import Lock
from typing import Dict, Any, List, Optional
import uuid
import statistics
import math

from app.services.farmer.price_service import (
    get_latest_price,
    rolling_stats,
    demand_supply_score
)

DEFAULT_FALLBACK_PRICE = 10.0   # configurable fallback


# defensive imports - fallbacks if not present
try:
    from app.services.farmer.harvest_grading_service import auto_grade_lot, compute_moisture_score
except Exception:
    auto_grade_lot = lambda lot_id: {}
    compute_moisture_score = lambda lot_id: {"score": None, "components": {}}

try:
    from app.services.farmer.traceability_service import get_lot
except Exception:
    get_lot = lambda lot_id: {}

try:
    from app.services.farmer.finance_service import add_ledger_entry
except Exception:
    add_ledger_entry = None

_lock = Lock()

# market prices indexed by crop (lowercase): {"wheat": {"price_per_kg": 18.0, "currency":"INR", "updated_at": iso}}
_market_prices: Dict[str, Dict[str, Any]] = {}

# historic suggested prices (audit)
_price_suggestions: Dict[str, Dict[str, Any]] = {}  # suggestion_id -> record
_suggestions_by_lot: Dict[str, List[str]] = {}      # lot_id -> [suggestion_ids]


def _now_iso():
    return datetime.utcnow().isoformat()

def _uid(prefix="ps"):
    return f"{prefix}_{uuid.uuid4()}"

# ---------------------
# Market price management
# ---------------------
def set_market_price(crop: str, price_per_kg: float, currency: str = "INR", source: Optional[str] = None) -> Dict[str, Any]:
    key = str(crop).lower()
    rec = {
        "crop": key,
        "price_per_kg": round(float(price_per_kg), 4),
        "currency": currency,
        "source": source or "manual",
        "updated_at": _now_iso()
    }
    with _lock:
        _market_prices[key] = rec
    return rec

def get_market_price(crop: str) -> Dict[str, Any]:
    return _market_prices.get(str(crop).lower(), {})

def list_market_prices() -> List[Dict[str, Any]]:
    with _lock:
        return list(_market_prices.values())

# ---------------------
# Core price suggestion logic
# ---------------------
def _grade_to_multiplier(grade: Optional[str], combined_score: Optional[float]) -> float:
    """
    Returns a multiplier based on grade and/or numeric score.
    - If grade present: A -> +10%; B -> 0%; C -> -10%
    - If numeric combined_score present, map 0..100 -> -15%..+15%
    Combine multiplicatively.
    """
    mult = 1.0
    if grade:
        g = str(grade).upper()
        if g == "A" or g == "PREMIUM":
            mult *= 1.10
        elif g == "B" or g == "STANDARD":
            mult *= 1.0
        else:
            mult *= 0.90

    if combined_score is not None:
        # map score 0->-0.15, 50->0.0, 100->+0.15 (linear)
        try:
            s = float(combined_score)
            score_adj = ((s - 50.0) / 50.0) * 0.15
            mult *= max(0.7, 1.0 + score_adj)  # clamp lower bound
        except Exception:
            pass

    return round(mult, 4)

def _moisture_and_dockage_penalty(ms_components: Dict[str, Any]) -> float:
    """
    Computes a multiplicative penalty for moisture and dockage.
    Returns a multiplier <= 1.0 (e.g., 0.85 reduces price 15%).
    Heuristics:
     - moisture above 12%: penalty grows 3% per % above up to 18, steeper beyond.
     - dockage reduces price by 1.5% per % dockage.
    """
    mult = 1.0
    try:
        avg_m = float(ms_components.get("avg_moisture_pct")) if ms_components.get("avg_moisture_pct") is not None else None
    except Exception:
        avg_m = None
    avg_d = float(ms_components.get("avg_dockage_pct", 0.0)) if ms_components.get("avg_dockage_pct") is not None else 0.0

    if avg_m is not None:
        if avg_m > 12.0:
            if avg_m <= 18.0:
                penalty_pct = (avg_m - 12.0) * 0.03
            else:
                penalty_pct = (6.0 * 0.03) + (avg_m - 18.0) * 0.06
            mult *= max(0.5, 1.0 - penalty_pct)

    # dockage penalty
    dock_pen = avg_d * 0.015
    mult *= max(0.5, 1.0 - dock_pen)

    return round(mult, 4)

def _age_adjustment(lot_record: Dict[str, Any]) -> float:
    """
    If lot is older (days since harvest), apply small negative adjustment.
    e.g., older than 30 days -> -5% per 30-day bucket (capped).
    """
    try:
        hd = lot_record.get("harvest_date")
        if not hd:
            return 1.0
        # support iso or date string
        try:
            from datetime import datetime as _dt
            dt = _dt.fromisoformat(hd)
        except Exception:
            try:
                from datetime import date as _date
                # fallback: parse yyyy-mm-dd
                parts = hd.split("T")[0]
                dt = _dt.fromisoformat(parts)
            except Exception:
                return 1.0
        days = (datetime.utcnow() - dt).days
        if days <= 7:
            return 1.0
        buckets = days // 30
        adj = max(0.7, 1.0 - 0.05 * buckets)
        return round(adj, 4)
    except Exception:
        return 1.0

def suggest_price_for_lot(
    lot_weight_kg: float,
    quality_score: Optional[float] = None,
    grade: Optional[str] = None,
    moisture_pct: Optional[float] = None,
    market_price_override: Optional[float] = None,
    demand_supply_override: Optional[float] = None,
    age_days: Optional[int] = None,
    crop: Optional[str] = None,
    market: Optional[str] = None
) -> Dict[str, Any]:
    """
    Enhanced version:
    - Auto-fetch market price from price_service
    - Auto-fetch rolling 7-day stats (volatility)
    - Auto-fetch demand-supply score
    """

    # ----------------------------------------------------
    # 1. GET BASE MARKET PRICE
    # ----------------------------------------------------
    base_price = None
    price_source = None

    # (A) explicit override
    if market_price_override:
        base_price = float(market_price_override)
        price_source = "manual_override"

    # (B) pull from price_service latest tick
    if base_price is None and crop and market:
        latest = get_latest_price(crop, market)
        if latest and latest.get("price_per_kg"):
            base_price = float(latest["price_per_kg"])
            price_source = "market_latest_tick"

    # (C) fallback: 7-day rolling average
    if base_price is None and crop and market:
        stats = rolling_stats(crop, market, days=7)
        if stats.get("avg"):
            base_price = float(stats["avg"])
            price_source = "market_rolling_avg"

    # (D) absolute fallback
    if base_price is None:
        base_price = DEFAULT_FALLBACK_PRICE
        price_source = "fallback_default"

    # ----------------------------------------------------
    # 2. GRADE MULTIPLIERS
    # ----------------------------------------------------
    grade_multipliers = {
        "A": 1.20,
        "B": 1.00,
        "C": 0.90,
        "D": 0.75
    }
    gmult = grade_multipliers.get(grade.upper(), 1.0) if grade else 1.0

    # ----------------------------------------------------
    # 3. MOISTURE PENALTY
    # ----------------------------------------------------
    m_penalty = 0.0
    if moisture_pct and moisture_pct > 12:
        m_penalty = (moisture_pct - 12) * 0.005   # 0.5% penalty per % over 12%

    # ----------------------------------------------------
    # 4. QUALITY BOOST
    # ----------------------------------------------------
    q_boost = 0.0
    if quality_score:
        q_boost = (quality_score - 50) * 0.003   # 0.3% per quality point above 50

    # ----------------------------------------------------
    # 5. AGE PENALTY
    # ----------------------------------------------------
    age_penalty = 0.0
    if age_days and age_days > 3:
        age_penalty = (age_days - 3) * 0.01      # 1% penalty per day after 3

    # ----------------------------------------------------
    # 6. DEMAND–SUPPLY MULTIPLIER
    # ----------------------------------------------------
    if demand_supply_override is not None:
        ds_score = demand_supply_override
        ds_source = "manual_override"
    else:
        ds = demand_supply_score(crop, market) if crop and market else {"score": 0}
        ds_score = ds.get("score", 0)
        ds_source = "auto_market_signal"

    ds_multiplier = 1 + (ds_score / 400.0)       # converts -100..100 → 0.75..1.25

    # ----------------------------------------------------
    # 7. APPLY ALL MULTIPLIERS
    # ----------------------------------------------------
    price = base_price
    price *= gmult
    price *= (1 + q_boost)
    price *= (1 - m_penalty)
    price *= (1 - age_penalty)
    price *= ds_multiplier

    price_per_kg = round(price, 2)
    total_price = round(price * lot_weight_kg, 2)

    return {
        "base_price": base_price,
        "price_source": price_source,
        "grade_multiplier": gmult,
        "quality_boost_pct": round(q_boost * 100, 2),
        "moisture_penalty_pct": round(m_penalty * 100, 2),
        "age_penalty_pct": round(age_penalty * 100, 2),
        "demand_supply_score": ds_score,
        "demand_supply_multiplier": round(ds_multiplier, 3),
        "ds_source": ds_source,
        "final_price_per_kg": price_per_kg,
        "total_value": total_price
    }

# ---------------------
# Bulk & simulation helpers
# ---------------------
def bulk_suggest_prices(lot_ids: List[str], supply_demand_multiplier: Optional[float] = None) -> Dict[str, Any]:
    out = []
    for lid in lot_ids:
        out.append(suggest_price_for_lot(lid, supply_demand_multiplier=supply_demand_multiplier))
    return {"count": len(out), "suggestions": out}

def simulate_price_sensitivity(
    lot_id: str,
    score_shock_percent: float = 10.0,
    sd_range: Optional[List[float]] = None
) -> Dict[str, Any]:
    """
    Simulate price changes for +/- score_shock_percent and different supply-demand multipliers.
    Returns list of scenarios.
    """
    base = suggest_price_for_lot(lot_id)
    base_score = base.get("combined_score") or 50.0
    sd_vals = sd_range or [0.9, 1.0, 1.1]
    scenarios = []
    for shock in (-score_shock_percent, 0.0, score_shock_percent):
        new_score = float(base_score) * (1.0 + shock / 100.0)
        # emulate by passing combined_score through grade multiplier hack: call grade_to_multiplier directly
        # We don't modify backend grade permanently; use the multiplier function approximated by score
        grade_mult_override = _grade_to_multiplier(base.get("grade"), new_score)
        # compute price using grade_mult_override and other multipliers from base
        computed = base["base_market_price"] * grade_mult_override * base["moisture_multiplier"] * base["age_multiplier"]
        for sd in sd_vals:
            scenarios.append({
                "score_shock_percent": shock,
                "sim_combined_score": round(new_score,2),
                "supply_demand": sd,
                "sim_price_per_kg": round(max(0.01, computed * sd), 4)
            })
    return {"lot_id": lot_id, "base": base, "scenarios": scenarios}

# ---------------------
# Audit & retrieval
# ---------------------
def get_suggestions_for_lot(lot_id: str) -> List[Dict[str, Any]]:
    ids = _suggestions_by_lot.get(lot_id, [])
    with _lock:
        return [ _price_suggestions[i].copy() for i in ids if i in _price_suggestions ]

def get_suggestion(suggestion_id: str) -> Dict[str, Any]:
    with _lock:
        return _price_suggestions.get(suggestion_id, {}).copy()

