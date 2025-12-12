"""
API Routes — Overall Predictions Bundle (Farmer POV)

Endpoints:
 - POST /farmer/predictions/bundle
 - GET  /farmer/predictions/bundle/{bundle_id}
 - GET  /farmer/predictions/bundle
"""

from fastapi import APIRouter, Query, HTTPException
from typing import Optional

from app.services.farmer import predictions_bundle_service as svc

router = APIRouter()


@router.post("/farmer/predictions/bundle")
async def api_generate_bundle(
    unit_id: str = Query(...),
    ndvi: Optional[float] = Query(None),
    canopy: Optional[float] = Query(None),
    humidity: Optional[float] = Query(None),
    temperature: Optional[float] = Query(None),
    soil_n: Optional[float] = Query(None),
    soil_p: Optional[float] = Query(None),
    soil_k: Optional[float] = Query(None),
    soil_moisture: Optional[float] = Query(None),
    growth_delta: Optional[float] = Query(None),
    notes: Optional[str] = Query(None)
):
    return svc.generate_predictions_bundle(
        unit_id=unit_id,
        ndvi=ndvi,
        canopy=canopy,
        humidity=humidity,
        temperature=temperature,
        soil_n=soil_n,
        soil_p=soil_p,
        soil_k=soil_k,
        soil_moisture=soil_moisture,
        growth_delta=growth_delta,
        notes=notes
    )


@router.get("/farmer/predictions/bundle/{bundle_id}")
def api_get_bundle(bundle_id: str):
    rec = svc.get_bundle(bundle_id)
    if not rec:
        raise HTTPException(status_code=404, detail="bundle_not_found")
    return rec


@router.get("/farmer/predictions/bundle")
def api_list_bundles(unit_id: Optional[str] = Query(None)):
    return svc.list_bundles(unit_id=unit_id)
