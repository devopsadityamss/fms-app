# backend/app/api/farmer/harvest_lot.py

from fastapi import APIRouter, Body, HTTPException, Query
from typing import Dict, Any, Optional

from app.services.farmer.harvest_lot_service import (
    create_harvest_lot,
    create_lot_from_harvest_event,
    get_harvest_lot,
    list_lots_by_farmer,
    list_lots_by_unit,
    update_harvest_lot,
    delete_harvest_lot,
    record_quality_test,
    list_quality_tests,
    compute_lot_quality_score,
    assign_storage,
    get_storage_assignment,
    transfer_lot,
    list_transfers_for_lot,
    allocate_from_lot,
    export_lots_csv
)

router = APIRouter()

# -----------------------
# CREATE / CRUD
# -----------------------
@router.post("/harvest/lot")
def api_create_lot(payload: Dict[str, Any] = Body(...)):
    required = ["farmer_id","crop","harvested_qty_kg"]
    for r in required:
        if r not in payload:
            raise HTTPException(status_code=400, detail=f"missing {r}")
    return create_harvest_lot(
        farmer_id=payload["farmer_id"],
        unit_id=payload.get("unit_id"),
        crop=payload["crop"],
        harvested_qty_kg=payload["harvested_qty_kg"],
        harvest_date_iso=payload.get("harvest_date"),
        seed_batch_id=payload.get("seed_batch_id"),
        moisture_pct=payload.get("moisture_pct"),
        initial_quality_notes=payload.get("initial_quality_notes"),
        metadata=payload.get("metadata")
    )

@router.post("/harvest/lot/from-harvest")
def api_create_lot_from_harvest(payload: Dict[str, Any] = Body(...)):
    required = ["farmer_id","unit_id","crop","harvested_qty_kg"]
    for r in required:
        if r not in payload:
            raise HTTPException(status_code=400, detail=f"missing {r}")
    return create_lot_from_harvest_event(
        farmer_id=payload["farmer_id"],
        unit_id=payload["unit_id"],
        crop=payload["crop"],
        harvested_qty_kg=payload["harvested_qty_kg"],
        harvest_date_iso=payload.get("harvest_date"),
        seed_batch_id=payload.get("seed_batch_id"),
        moisture_pct=payload.get("moisture_pct"),
        metadata=payload.get("metadata")
    )

@router.get("/harvest/lot/{lot_id}")
def api_get_lot(lot_id: str):
    res = get_harvest_lot(lot_id)
    if not res:
        raise HTTPException(status_code=404, detail="lot_not_found")
    return res

@router.get("/harvest/lots/farmer/{farmer_id}")
def api_list_lots_farmer(farmer_id: str):
    return {"farmer_id": farmer_id, "lots": list_lots_by_farmer(farmer_id)}

@router.get("/harvest/lots/unit/{unit_id}")
def api_list_lots_unit(unit_id: str):
    return {"unit_id": unit_id, "lots": list_lots_by_unit(unit_id)}

@router.put("/harvest/lot/{lot_id}")
def api_update_lot(lot_id: str, updates: Dict[str, Any] = Body(...)):
    res = update_harvest_lot(lot_id, updates)
    if res.get("error"):
        raise HTTPException(status_code=404, detail=res)
    return res

@router.delete("/harvest/lot/{lot_id}")
def api_delete_lot(lot_id: str):
    res = delete_harvest_lot(lot_id)
    if res.get("error"):
        raise HTTPException(status_code=404, detail=res)
    return res

# -----------------------
# QUALITY / TESTS
# -----------------------
@router.post("/harvest/lot/{lot_id}/quality-test")
def api_quality_test(lot_id: str, payload: Dict[str, Any] = Body(...)):
    return record_quality_test(
        lot_id=lot_id,
        tester=payload.get("tester"),
        moisture_pct=payload.get("moisture_pct"),
        dockage_pct=payload.get("dockage_pct"),
        grade=payload.get("grade"),
        protein_pct=payload.get("protein_pct"),
        notes=payload.get("notes"),
        metadata=payload.get("metadata")
    )

@router.get("/harvest/lot/{lot_id}/quality-tests")
def api_list_tests(lot_id: str):
    return {"lot_id": lot_id, "tests": list_quality_tests(lot_id)}

@router.get("/harvest/lot/{lot_id}/quality-score")
def api_quality_score(lot_id: str):
    return compute_lot_quality_score(lot_id)

# -----------------------
# STORAGE / TRANSFERS / ALLOCATION
# -----------------------
@router.post("/harvest/lot/{lot_id}/assign-storage")
def api_assign_storage(lot_id: str, payload: Dict[str, Any] = Body(...)):
    storage_id = payload.get("storage_id")
    location_name = payload.get("location_name")
    if not storage_id:
        raise HTTPException(status_code=400, detail="missing storage_id")
    return assign_storage(lot_id, storage_id, location_name=location_name, stored_at_iso=payload.get("stored_at"))

@router.get("/harvest/lot/{lot_id}/storage")
def api_get_storage(lot_id: str):
    return get_storage_assignment(lot_id)

@router.post("/harvest/lot/{lot_id}/transfer")
def api_transfer_lot(lot_id: str, payload: Dict[str, Any] = Body(...)):
    to_storage = payload.get("to_storage_id")
    if not to_storage:
        raise HTTPException(status_code=400, detail="missing to_storage_id")
    return transfer_lot(lot_id, to_storage, moved_by=payload.get("moved_by"), notes=payload.get("notes"))

@router.get("/harvest/lot/{lot_id}/transfers")
def api_list_transfers(lot_id: str):
    return {"lot_id": lot_id, "transfers": list_transfers_for_lot(lot_id)}

@router.post("/harvest/lot/{lot_id}/allocate")
def api_allocate_from_lot(lot_id: str, payload: Dict[str, Any] = Body(...)):
    qty = payload.get("qty_kg")
    if qty is None:
        raise HTTPException(status_code=400, detail="missing qty_kg")
    return allocate_from_lot(lot_id, float(qty), purpose=payload.get("purpose"))

@router.get("/harvest/lots/{farmer_id}/export")
def api_export_lots(farmer_id: str):
    csv_str = export_lots_csv(farmer_id)
    if not csv_str:
        raise HTTPException(status_code=404, detail="no_lots")
    return {"csv": csv_str}
