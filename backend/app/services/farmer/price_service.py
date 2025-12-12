# backend/app/services/farmer/price_service.py

"""
Market Price Aggregator & Dynamic Pricing Suggestions (in-memory)

Features:
 - ingest price tick (source, commodity, market, price_per_kg, timestamp)
 - get latest price for commodity+market
 - compute rolling averages (N-day), min/max, volatility (std dev)
 - price watches: user can register watch with target price or % change triggers
 - evaluate a recommended sell price for a farmer given transport cost, quality premium, desired_margin_pct
 - simple demand-supply score (heuristic) derived from price movement
 - list historical price series (limited)
 - note: notification integration is left as a callback stub for when you wire notification_service
"""

from datetime import datetime, timedelta
from threading import Lock
from typing import Dict, Any, List, Optional
import uuid
import statistics

_lock = Lock()

# Stores
_price_ticks: Dict[str, List[Dict[str, Any]]] = {}  # key = f"{commodity}::{market}" -> list of ticks sorted by time asc
_latest_index: Dict[str, Dict[str, Any]] = {}      # same key -> latest tick
_price_watches: Dict[str, Dict[str, Any]] = {}     # watch_id -> watch record

# Helpers
def _key(commodity: str, market: str) -> str:
    return f"{commodity.lower()}::{market.lower()}"

def _now_iso():
    return datetime.utcnow().isoformat()


# -------------------------
# Ingesting & retrieving ticks
# -------------------------
def ingest_price_tick(
    source: str,
    commodity: str,
    market: str,
    price_per_kg: float,
    timestamp_iso: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    ts = timestamp_iso or _now_iso()
    rec = {
        "tick_id": f"tick_{uuid.uuid4()}",
        "source": source,
        "commodity": commodity.lower(),
        "market": market.lower(),
        "price_per_kg": float(price_per_kg),
        "timestamp_iso": ts,
        "metadata": metadata or {}
    }
    k = _key(commodity, market)
    with _lock:
        _price_ticks.setdefault(k, []).append(rec)
        # keep ticks sorted by timestamp (append usually keeps order)
        _latest_index[k] = rec
    return rec

def get_latest_price(commodity: str, market: str) -> Dict[str, Any]:
    k = _key(commodity, market)
    return _latest_index.get(k, {})

def list_price_series(commodity: str, market: str, limit: int = 500) -> List[Dict[str, Any]]:
    k = _key(commodity, market)
    with _lock:
        series = list(_price_ticks.get(k, []))
    return series[-limit:]


# -------------------------
# Rolling stats & volatility
# -------------------------
def rolling_stats(commodity: str, market: str, days: int = 7) -> Dict[str, Any]:
    """
    Compute rolling average, min, max, stddev for last `days`.
    """
    k = _key(commodity, market)
    cutoff = datetime.utcnow() - timedelta(days=days)
    with _lock:
        ticks = list(_price_ticks.get(k, []))
    recent = []
    for t in ticks:
        try:
            if datetime.fromisoformat(t["timestamp_iso"]) >= cutoff:
                recent.append(t["price_per_kg"])
        except Exception:
            recent.append(t["price_per_kg"])
    if not recent:
        return {"commodity": commodity, "market": market, "days": days, "count": 0}
    avg = round(statistics.mean(recent), 2)
    mn = round(min(recent), 2)
    mx = round(max(recent), 2)
    sd = round(statistics.pstdev(recent), 4) if len(recent) > 1 else 0.0
    change_pct = round(((recent[-1] - recent[0]) / recent[0]) * 100, 2) if recent[0] != 0 else 0.0
    return {"commodity": commodity, "market": market, "days": days, "count": len(recent), "avg": avg, "min": mn, "max": mx, "stddev": sd, "change_pct": change_pct}


# -------------------------
# Price watches (alerts)
# -------------------------
def create_price_watch(
    user_id: str,
    commodity: str,
    market: str,
    target_price: Optional[float] = None,
    target_pct_increase: Optional[float] = None,
    active: bool = True,
    metadata: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    wid = f"watch_{uuid.uuid4()}"
    rec = {
        "watch_id": wid,
        "user_id": user_id,
        "commodity": commodity.lower(),
        "market": market.lower(),
        "target_price": float(target_price) if target_price is not None else None,
        "target_pct_increase": float(target_pct_increase) if target_pct_increase is not None else None,
        "active": bool(active),
        "created_at": _now_iso(),
        "metadata": metadata or {}
    }
    with _lock:
        _price_watches[wid] = rec
    return rec

def list_price_watches(user_id: Optional[str] = None) -> List[Dict[str, Any]]:
    with _lock:
        items = list(_price_watches.values())
    if user_id:
        items = [i for i in items if i.get("user_id") == user_id]
    return items

def deactivate_price_watch(watch_id: str) -> Dict[str, Any]:
    with _lock:
        w = _price_watches.get(watch_id)
        if not w:
            return {"error": "watch_not_found"}
        w["active"] = False
        w["deactivated_at"] = _now_iso()
        _price_watches[watch_id] = w
    return w

def evaluate_watches_and_trigger(callback: Optional[callable] = None) -> Dict[str, Any]:
    """
    Evaluate active watches. If condition met, call callback(payload) where payload contains watch & latest tick.
    callback is best-effort (user should pass in a notifier).
    """
    triggered = []
    with _lock:
        watches = list(_price_watches.values())
    for w in watches:
        if not w.get("active"):
            continue
        latest = get_latest_price(w["commodity"], w["market"])
        if not latest:
            continue
        price = float(latest["price_per_kg"])
        fired = False
        reason = None
        if w.get("target_price") is not None and price >= float(w["target_price"]):
            fired = True
            reason = f"price_reached:{price} >= {w['target_price']}"
        if not fired and w.get("target_pct_increase") is not None:
            # compute pct change over 7 days
            stats = rolling_stats(w["commodity"], w["market"], days=7)
            if stats.get("count",0) and abs(stats.get("change_pct",0)) >= float(w["target_pct_increase"]):
                fired = True
                reason = f"pct_change:{stats.get('change_pct')}"
        if fired:
            payload = {"watch": w, "latest": latest, "reason": reason}
            triggered.append(payload)
            try:
                if callback:
                    callback(payload)
            except Exception:
                pass
            # optionally deactivate one-shot watches (left as active by default)
    return {"triggered_count": len(triggered), "triggered": triggered}


# -------------------------
# Dynamic pricing suggestion
# -------------------------
def suggest_sell_price(
    farmer_id: str,
    commodity: str,
    market: str,
    quality_premium_pct: Optional[float] = 0.0,
    transport_cost_per_kg: Optional[float] = 0.0,
    desired_margin_pct: Optional[float] = 10.0,
    risk_aversion: Optional[float] = 0.5
) -> Dict[str, Any]:
    """
    Suggest a sell price per kg based on latest market price, quality premium, transport cost, and desired margin.
    risk_aversion: 0.0 (aggressive — wait for better price) .. 1.0 (conservative — sell at market)
    Algorithm (heuristic):
      base = latest_market_price
      target = base * (1 + quality_premium_pct/100) - transport_cost_per_kg
      desired = target * (1 + desired_margin_pct/100)
      suggested = blend between market(base) and desired by (1 - risk_aversion)
    """
    latest = get_latest_price(commodity, market)
    if not latest:
        return {"error": "no_market_price"}
    base = float(latest["price_per_kg"])
    qp = float(quality_premium_pct or 0.0) / 100.0
    transport = float(transport_cost_per_kg or 0.0)
    desired_margin = float(desired_margin_pct or 10.0) / 100.0
    target = (base * (1 + qp)) - transport
    desired = target * (1 + desired_margin)
    # clamp desired >= base*0.8 to avoid suggesting extreme low
    desired = max(desired, base * 0.8)
    # blend
    suggested = (risk_aversion * base) + ((1.0 - risk_aversion) * desired)
    # compute recommended action
    stats7 = rolling_stats(commodity, market, days=7)
    volatility = stats7.get("stddev", 0.0)
    action = "hold" if (desired > base and volatility < (base * 0.05)) else "consider_sell" if desired <= base or volatility >= (base * 0.1) else "monitor"
    return {
        "commodity": commodity,
        "market": market,
        "latest_market_price": base,
        "target_after_premium_minus_transport": round(target, 2),
        "desired_price_with_margin": round(desired, 2),
        "suggested_price": round(suggested, 2),
        "volatility_7d": volatility,
        "recommended_action": action,
        "stats_7d": stats7
    }


# -------------------------
# Demand-supply heuristic
# -------------------------
def demand_supply_score(commodity: str, market: str, days: int = 14) -> Dict[str, Any]:
    """
    Heuristic: rising price + high volatility => supply shortfall (positive demand pressure).
    Falling price + low volatility => oversupply.
    Return score -100..+100 where positive means demand > supply.
    """
    stats = rolling_stats(commodity, market, days=days)
    if not stats.get("count"):
        return {"score": 0, "reason": "no_data"}
    change = stats.get("change_pct", 0.0)
    vol = stats.get("stddev", 0.0)
    # normalize vol relative to avg
    avg = stats.get("avg", 1.0) or 1.0
    vol_norm = (vol / avg) * 100.0
    score = change * 1.0 + vol_norm * 0.5
    # clamp
    score = max(-100.0, min(100.0, score))
    reason = {"change_pct": change, "volatility_pct": round(vol_norm,2)}
    return {"score": round(score,2), "reason": reason, "stats": stats}
