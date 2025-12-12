"""
API Routes — Profitability Simulation (Farmer POV)
--------------------------------------------------

Endpoints:
 - POST /farmer/profitability/simulate
 - GET  /farmer/profitability/{sim_id}
 - GET  /farmer/profitability
"""

from fastapi import APIRouter, HTTPException, Query, Body
from typing import Optional, Dict, Any

from app.services.farmer import profitability_simulation_service as svc

router = APIRouter()


@router.post("/farmer/profitability/simulate")
async def api_run_simulation(
    yield_kg: float = Query(...),
    price_per_kg: float = Query(...),
    scenario: Optional[str] = Query(None),
    unit_id: Optional[str] = Query(None),
    notes: Optional[str] = Query(None),
    variable_costs: Optional[Dict[str, float]] = Body(None),
    fixed_costs: Optional[Dict[str, float]] = Body(None)
):
    """
    variable_costs and fixed_costs are JSON bodies, e.g.:

    {
        "labor": 1200,
        "fertilizer": 3000
    }
    """
    return svc.run_profitability_simulation(
        yield_kg=yield_kg,
        price_per_kg=price_per_kg,
        variable_costs=variable_costs,
        fixed_costs=fixed_costs,
        scenario=scenario,
        unit_id=unit_id,
        notes=notes
    )


@router.get("/farmer/profitability/{sim_id}")
def api_get_simulation(sim_id: str):
    rec = svc.get_simulation(sim_id)
    if not rec:
        raise HTTPException(status_code=404, detail="simulation_not_found")
    return rec


@router.get("/farmer/profitability")
def api_list_simulations(unit_id: Optional[str] = Query(None)):
    return svc.list_simulations(unit_id=unit_id)
