# backend/app/api/farmer/traceability.py

from fastapi import APIRouter, Body, HTTPException, Query
from typing import Dict, Any, Optional

from app.services.farmer.traceability_service import (
    create_lot,
    create_batch,
    get_lot,
    list_lots_for_farmer,
    delete_lot,
    attach_doc_to_lot,
    detach_doc_from_lot,
    record_event,
    transfer_lot,
    record_sale,
    list_sales_for_lot,
    get_sale,
    get_trace_for_lot,
    get_trace_for_farmer,
    provenance_report,
    export_trace_csv,
    export_trace_json,
    generate_trace_certificate,
    qr_payload_for_lot
)

router = APIRouter()

# -----------------------
# Create / CRUD
# -----------------------
@router.post("/trace/lot")
def api_create_lot(payload: Dict[str, Any] = Body(...)):
    required = ["farmer_id","crop","harvested_qty_kg"]
    for r in required:
        if r not in payload:
            raise HTTPException(status_code=400, detail=f"missing {r}")
    return create_lot(
        farmer_id=payload["farmer_id"],
        unit_id=payload.get("unit_id"),
        crop=payload["crop"],
        harvested_qty_kg=payload["harvested_qty_kg"],
        harvest_date_iso=payload.get("harvest_date"),
        variety=payload.get("variety"),
        grade=payload.get("grade"),
        doc_refs=payload.get("doc_refs"),
        metadata=payload.get("metadata"),
    )

# backward-compatible batch creation
@router.post("/trace/batch")
def api_create_batch(payload: Dict[str, Any] = Body(...)):
    required = ["farmer_id","unit_id","crop","total_weight_kg"]
    for r in required:
        if r not in payload:
            raise HTTPException(status_code=400, detail=f"missing {r}")
    return create_batch(
        farmer_id=payload["farmer_id"],
        unit_id=payload["unit_id"],
        crop=payload["crop"],
        variety=payload.get("variety"),
        harvest_date_iso=payload.get("harvest_date"),
        total_weight_kg=payload["total_weight_kg"],
        grade=payload.get("grade"),
        doc_refs=payload.get("doc_refs"),
        metadata=payload.get("metadata")
    )

@router.get("/trace/lot/{lot_id}")
def api_get_lot(lot_id: str):
    res = get_lot(lot_id)
    if not res:
        raise HTTPException(status_code=404, detail="lot_not_found")
    return res

@router.get("/trace/lots/farmer/{farmer_id}")
def api_list_lots_farmer(farmer_id: str):
    return {"farmer_id": farmer_id, "lots": list_lots_for_farmer(farmer_id)}

@router.delete("/trace/lot/{lot_id}")
def api_delete_lot(lot_id: str):
    res = delete_lot(lot_id)
    if res.get("error"):
        raise HTTPException(status_code=404, detail=res)
    return res

# -----------------------
# Docs
# -----------------------
@router.post("/trace/lot/{lot_id}/attach-doc")
def api_attach_doc(lot_id: str, payload: Dict[str, Any] = Body(...)):
    if "doc_ref" not in payload:
        raise HTTPException(status_code=400, detail="missing doc_ref")
    return attach_doc_to_lot(lot_id, payload["doc_ref"], doc_type=payload.get("type"), uploaded_by=payload.get("uploaded_by"))

@router.post("/trace/lot/{lot_id}/detach-doc")
def api_detach_doc(lot_id: str, payload: Dict[str, Any] = Body(...)):
    if "doc_ref" not in payload:
        raise HTTPException(status_code=400, detail="missing doc_ref")
    return detach_doc_from_lot(lot_id, payload["doc_ref"])

# -----------------------
# Events & transfer
# -----------------------
@router.post("/trace/lot/{lot_id}/event")
def api_record_event(lot_id: str, payload: Dict[str, Any] = Body(...)):
    if "type" not in payload or "actor" not in payload:
        raise HTTPException(status_code=400, detail="missing type or actor")
    return record_event(lot_id, payload["type"], payload["actor"], note=payload.get("note"), metadata=payload.get("metadata"))

@router.post("/trace/lot/{lot_id}/transfer")
def api_transfer_lot(lot_id: str, payload: Dict[str, Any] = Body(...)):
    if "from_actor" not in payload or "to_actor" not in payload:
        raise HTTPException(status_code=400, detail="missing from_actor or to_actor")
    return transfer_lot(lot_id, payload["from_actor"], payload["to_actor"], note=payload.get("note"))

# -----------------------
# Sales
# -----------------------
@router.post("/trace/lot/{lot_id}/sale")
def api_record_sale(lot_id: str, payload: Dict[str, Any] = Body(...)):
    required = ["buyer_name","qty_kg","price_per_kg"]
    for r in required:
        if r not in payload:
            raise HTTPException(status_code=400, detail=f"missing {r}")
    return record_sale(
        lot_id=lot_id,
        buyer_name=payload["buyer_name"],
        buyer_id=payload.get("buyer_id"),
        qty_kg=float(payload["qty_kg"]),
        price_per_kg=float(payload["price_per_kg"]),
        sold_by=payload.get("sold_by"),
        metadata=payload.get("metadata")
    )

@router.get("/trace/lot/{lot_id}/sales")
def api_list_sales(lot_id: str):
    return {"lot_id": lot_id, "sales": list_sales_for_lot(lot_id)}

@router.get("/trace/sale/{sale_id}")
def api_get_sale(sale_id: str):
    s = get_sale(sale_id)
    if not s:
        raise HTTPException(status_code=404, detail="sale_not_found")
    return s

# -----------------------
# Trace / provenance / export
# -----------------------
@router.get("/trace/lot/{lot_id}/trace")
def api_get_trace(lot_id: str):
    return get_trace_for_lot(lot_id)

@router.get("/trace/farmer/{farmer_id}")
def api_get_trace_farmer(farmer_id: str):
    return get_trace_for_farmer(farmer_id)

@router.get("/trace/lot/{lot_id}/provenance")
def api_provenance(lot_id: str):
    res = provenance_report(lot_id)
    if res.get("error"):
        raise HTTPException(status_code=404, detail=res)
    return res

@router.get("/trace/lot/{lot_id}/export/csv")
def api_export_csv(lot_id: str):
    csv_str = export_trace_csv(lot_id)
    if not csv_str:
        raise HTTPException(status_code=404, detail="no_trace")
    return {"csv": csv_str}

@router.get("/trace/lot/{lot_id}/export/json")
def api_export_json(lot_id: str):
    return export_trace_json(lot_id)

# -----------------------
# Certificate & QR
# -----------------------
@router.post("/trace/lot/{lot_id}/certificate")
def api_generate_certificate(lot_id: str, payload: Dict[str, Any] = Body(None)):
    issuer = payload.get("issuer") if payload else None
    notes = payload.get("notes") if payload else None
    cert = generate_trace_certificate(lot_id, issuer=issuer, notes=notes)
    if cert.get("error"):
        raise HTTPException(status_code=404, detail=cert)
    return cert

@router.get("/trace/lot/{lot_id}/qr")
def api_qr_payload(lot_id: str):
    res = qr_payload_for_lot(lot_id)
    if res.get("error"):
        raise HTTPException(status_code=404, detail=res)
    return res
