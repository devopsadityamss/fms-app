# backend/app/api/farmer/adaptive_intelligence.py

from fastapi import APIRouter, Body, Query, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any, List

from app.services.farmer.adaptive_intelligence_service import (
    get_farmer_profile,
    update_farmer_intelligence_profile,
    get_modifiers_for_farmer,
    set_manual_modifier,
    auto_update_profiles,
    get_all_profiles
)

router = APIRouter()

class UpdateProfileRequest(BaseModel):
    farmer_id: str
    recent_unit_ids: Optional[List[str]] = None
    lookback_days: Optional[int] = 30

class ManualModifierRequest(BaseModel):
    key: str
    value: Optional[Any] = None

class AutoUpdateRequest(BaseModel):
    farmer_unit_map: Dict[str, List[str]]
    lookback_days: Optional[int] = 30

@router.get("/intelligence-profile/{farmer_id}")
def api_get_profile(farmer_id: str):
    return get_farmer_profile(farmer_id)

@router.post("/intelligence-profile/{farmer_id}/update")
def api_update_profile(farmer_id: str, payload: UpdateProfileRequest = Body(...)):
    # payload.farmer_id is redundant (path param); use path param
    res = update_farmer_intelligence_profile(farmer_id, recent_unit_ids=payload.recent_unit_ids, lookback_days=payload.lookback_days or 30)
    return res

@router.get("/intelligence-profile/{farmer_id}/modifiers")
def api_get_modifiers(farmer_id: str):
    return {"farmer_id": farmer_id, "modifiers": get_modifiers_for_farmer(farmer_id)}

@router.post("/intelligence-profile/{farmer_id}/modifier")
def api_set_modifier(farmer_id: str, payload: ManualModifierRequest = Body(...)):
    if not payload.key:
        raise HTTPException(status_code=400, detail="key_required")
    res = set_manual_modifier(farmer_id, payload.key, payload.value)
    return res

@router.post("/intelligence-profile/auto-update")
def api_auto_update(payload: AutoUpdateRequest = Body(...)):
    res = auto_update_profiles(payload.farmer_unit_map, lookback_days=payload.lookback_days or 30)
    return res

@router.get("/intelligence-profile/all")
def api_list_profiles():
    return get_all_profiles()
