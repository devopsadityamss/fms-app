# backend/app/api/farmer/seed.py

from fastapi import APIRouter, Body, HTTPException, Query
from typing import Dict, Any, Optional

from app.services.farmer.seed_service import (
    create_seed_batch,
    get_seed_batch,
    list_seed_batches,
    update_seed_batch,
    delete_seed_batch,
    allocate_seed,
    list_allocations,
    record_germination_test,
    list_germination_tests,
    latest_germination_rate,
    predict_germination_rate,
    list_near_expiry_batches,
    list_expired_batches,
    export_batches_csv
)

router = APIRouter()


@router.post("/seed/batch")
def api_create_batch(payload: Dict[str, Any] = Body(...)):
    required = ["farmer_id", "variety", "quantity_kg"]
    for r in required:
        if r not in payload:
            raise HTTPException(status_code=400, detail=f"missing {r}")
    return create_seed_batch(
        farmer_id=payload["farmer_id"],
        variety=payload["variety"],
        supplier=payload.get("supplier"),
        lot_no=payload.get("lot_no"),
        quantity_kg=payload["quantity_kg"],
        date_received_iso=payload.get("date_received"),
        expiry_date_iso=payload.get("expiry_date"),
        treatment=payload.get("treatment"),
        metadata=payload.get("metadata")
    )

@router.get("/seed/batch/{batch_id}")
def api_get_batch(batch_id: str):
    res = get_seed_batch(batch_id)
    if not res:
        raise HTTPException(status_code=404, detail="batch_not_found")
    return res

@router.get("/seed/batches/{farmer_id}")
def api_list_batches(farmer_id: str, include_empty: bool = Query(False)):
    return {"farmer_id": farmer_id, "batches": list_seed_batches(farmer_id, include_empty=include_empty)}

@router.put("/seed/batch/{batch_id}")
def api_update_batch(batch_id: str, updates: Dict[str, Any] = Body(...)):
    res = update_seed_batch(batch_id, updates)
    if res.get("error"):
        raise HTTPException(status_code=404, detail=res)
    return res

@router.delete("/seed/batch/{batch_id}")
def api_delete_batch(batch_id: str):
    res = delete_seed_batch(batch_id)
    if res.get("error"):
        raise HTTPException(status_code=404, detail=res)
    return res

@router.post("/seed/batch/{batch_id}/allocate")
def api_allocate(batch_id: str, payload: Dict[str, Any] = Body(...)):
    qty = payload.get("qty_kg")
    purpose = payload.get("purpose", "usage")
    reserved_by = payload.get("reserved_by")
    if qty is None:
        raise HTTPException(status_code=400, detail="missing qty_kg")
    res = allocate_seed(batch_id, purpose, float(qty), reserved_by=reserved_by)
    if res.get("error"):
        raise HTTPException(status_code=400, detail=res)
    return res

@router.get("/seed/batch/{batch_id}/allocations")
def api_list_allocs(batch_id: str):
    return {"batch_id": batch_id, "allocations": list_allocations(batch_id)}

@router.post("/seed/batch/{batch_id}/germ-test")
def api_record_germ_test(batch_id: str, payload: Dict[str, Any] = Body(...)):
    required = ["sample_size","germinated_count"]
    for r in required:
        if r not in payload:
            raise HTTPException(status_code=400, detail=f"missing {r}")
    return record_germination_test(batch_id, int(payload["sample_size"]), int(payload["germinated_count"]), date_iso=payload.get("date"), moisture_pct=payload.get("moisture_pct"), notes=payload.get("notes"))

@router.get("/seed/batch/{batch_id}/germ-tests")
def api_list_tests(batch_id: str):
    return {"batch_id": batch_id, "tests": list_germination_tests(batch_id)}

@router.get("/seed/batch/{batch_id}/germ-rate")
def api_latest_germ_rate(batch_id: str):
    r = latest_germination_rate(batch_id)
    if r is None:
        raise HTTPException(status_code=404, detail="no_tests")
    return {"batch_id": batch_id, "latest_germination_pct": r}

@router.get("/seed/batch/{batch_id}/predict-germ")
def api_predict_germ(batch_id: str, use_history: bool = Query(True)):
    return predict_germination_rate(batch_id, use_history=use_history)

@router.get("/seed/batches/{farmer_id}/near-expiry")
def api_near_expiry(farmer_id: str, within_days: int = Query(30)):
    return {"farmer_id": farmer_id, "near_expiry": list_near_expiry_batches(farmer_id, within_days=within_days)}

@router.get("/seed/batches/{farmer_id}/expired")
def api_expired(farmer_id: str):
    return {"farmer_id": farmer_id, "expired": list_expired_batches(farmer_id)}

@router.get("/seed/batches/{farmer_id}/export")
def api_export(farmer_id: str):
    csv_str = export_batches_csv(farmer_id)
    if not csv_str:
        raise HTTPException(status_code=404, detail="no_batches")
    return {"csv": csv_str}
