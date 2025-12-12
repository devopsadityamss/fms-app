from fastapi import APIRouter, Body, HTTPException, Query
from typing import Dict, Any, List, Optional

from app.services.farmer.pricing_service import (
    set_market_price,
    get_market_price,
    list_market_prices,
    suggest_price_for_lot,
    bulk_suggest_prices,
    simulate_price_sensitivity,
    get_suggestions_for_lot,
    get_suggestion
)

router = APIRouter()

# -------------------------------------------------------
# MARKET PRICE MANAGEMENT
# -------------------------------------------------------

@router.post("/pricing/market")
def api_set_market_price(payload: Dict[str, Any] = Body(...)):
    """
    Set or update market price for a crop.
    Payload:
        - crop
        - price_per_kg
        - currency (optional)
        - source (optional)
    """
    crop = payload.get("crop")
    price = payload.get("price_per_kg")

    if not crop or price is None:
        raise HTTPException(400, detail="Missing crop or price_per_kg")

    return set_market_price(
        crop=crop,
        price_per_kg=float(price),
        currency=payload.get("currency", "INR"),
        source=payload.get("source")
    )


@router.get("/pricing/market/{crop}")
def api_get_market_price(crop: str):
    res = get_market_price(crop)
    if not res:
        raise HTTPException(404, detail="market_price_not_found")
    return res


@router.get("/pricing/markets")
def api_list_market_prices():
    return {"count": len(list_market_prices()), "markets": list_market_prices()}


# -------------------------------------------------------
# PRICE SUGGESTION ENGINE
# -------------------------------------------------------

@router.post("/pricing/suggest")
def api_suggest_price(payload: Dict[str, Any] = Body(...)):
    """
    Suggest price for a harvest lot.

    Payload fields expected:
        - lot_weight_kg
        - quality_score (optional)
        - grade (optional)
        - moisture_pct (optional)
        - market_price_override (optional)
        - demand_supply_override (optional)
        - age_days (optional)
        - crop (optional)
        - market (optional)
    """
    return suggest_price_for_lot(**payload)


@router.post("/pricing/bulk")
def api_bulk_suggest(payload: Dict[str, Any] = Body(...)):
    lot_ids = payload.get("lot_ids")
    sd = payload.get("supply_demand_multiplier")

    if not lot_ids:
        raise HTTPException(400, detail="missing lot_ids")

    return bulk_suggest_prices(lot_ids, supply_demand_multiplier=sd)


@router.get("/pricing/simulate/{lot_id}")
def api_simulate_price(
    lot_id: str,
    score_shock_percent: float = Query(10.0),
    sd_values: Optional[str] = Query(None)
):
    sd_list = None
    if sd_values:
        try:
            sd_list = [float(x) for x in sd_values.split(",")]
        except:
            raise HTTPException(400, detail="Invalid sd_values format. Use comma-separated floats.")

    return simulate_price_sensitivity(
        lot_id=lot_id,
        score_shock_percent=score_shock_percent,
        sd_range=sd_list
    )


# -------------------------------------------------------
# SUGGESTION HISTORY
# -------------------------------------------------------

@router.get("/pricing/lot/{lot_id}/suggestions")
def api_get_lot_suggestions(lot_id: str):
    return {
        "lot_id": lot_id,
        "suggestions": get_suggestions_for_lot(lot_id)
    }


@router.get("/pricing/suggestion/{suggestion_id}")
def api_get_single_suggestion(suggestion_id: str):
    res = get_suggestion(suggestion_id)
    if not res:
        raise HTTPException(404, detail="suggestion_not_found")
    return res
