# backend/app/api/farmer/price.py

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any, List

from app.services.farmer.price_service import (
    ingest_price_tick,
    get_latest_price,
    list_price_series,
    rolling_stats,
    create_price_watch,
    list_price_watches,
    deactivate_price_watch,
    evaluate_watches_and_trigger,
    suggest_sell_price,
    demand_supply_score
)

router = APIRouter()

# Payloads
class PriceTickPayload(BaseModel):
    source: str
    commodity: str
    market: str
    price_per_kg: float
    timestamp_iso: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

class PriceWatchPayload(BaseModel):
    user_id: str
    commodity: str
    market: str
    target_price: Optional[float] = None
    target_pct_increase: Optional[float] = None
    metadata: Optional[Dict[str, Any]] = None

# Endpoints
@router.post("/farmer/price/ingest")
def api_ingest_tick(req: PriceTickPayload):
    return ingest_price_tick(req.source, req.commodity, req.market, req.price_per_kg, timestamp_iso=req.timestamp_iso, metadata=req.metadata)

@router.get("/farmer/price/latest")
def api_latest(commodity: str, market: str):
    res = get_latest_price(commodity, market)
    if not res:
        raise HTTPException(status_code=404, detail="no_price_found")
    return res

@router.get("/farmer/price/series")
def api_series(commodity: str, market: str, limit: Optional[int] = 500):
    return {"series": list_price_series(commodity, market, limit=limit or 500)}

@router.get("/farmer/price/stats")
def api_stats(commodity: str, market: str, days: Optional[int] = 7):
    return rolling_stats(commodity, market, days=days or 7)

@router.post("/farmer/price/watch")
def api_create_watch(req: PriceWatchPayload):
    return create_price_watch(req.user_id, req.commodity, req.market, target_price=req.target_price, target_pct_increase=req.target_pct_increase, metadata=req.metadata)

@router.get("/farmer/price/watches")
def api_list_watches(user_id: Optional[str] = None):
    return {"watches": list_price_watches(user_id=user_id)}

@router.post("/farmer/price/watch/{watch_id}/deactivate")
def api_deactivate_watch(watch_id: str):
    res = deactivate_price_watch(watch_id)
    if "error" in res:
        raise HTTPException(status_code=404, detail=res["error"])
    return res

@router.post("/farmer/price/watches/evaluate")
def api_eval_watches():
    # manual trigger — in production you can call this from a scheduler and wire a notification callback
    return evaluate_watches_and_trigger()

@router.get("/farmer/price/suggest")
def api_suggest(commodity: str, market: str, quality_premium_pct: Optional[float] = 0.0, transport_cost_per_kg: Optional[float] = 0.0, desired_margin_pct: Optional[float] = 10.0, risk_aversion: Optional[float] = 0.5):
    res = suggest_sell_price("farmer", commodity, market, quality_premium_pct=quality_premium_pct, transport_cost_per_kg=transport_cost_per_kg, desired_margin_pct=desired_margin_pct, risk_aversion=risk_aversion)
    if "error" in res:
        raise HTTPException(status_code=404, detail=res["error"])
    return res

@router.get("/farmer/price/demand_supply")
def api_demand_supply(commodity: str, market: str, days: Optional[int] = 14):
    return demand_supply_score(commodity, market, days=days or 14)
