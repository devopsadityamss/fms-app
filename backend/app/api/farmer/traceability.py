# backend/app/api/farmer/traceability.py

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any, List

from app.services.farmer.traceability_service import (
    create_batch,
    get_batch,
    list_batches_for_farmer,
    record_event,
    get_batch_events,
    transfer_batch,
    attach_doc_to_batch,
    detach_doc_from_batch,
    provenance_report,
    qr_payload_for_batch
)

router = APIRouter()


class CreateBatchPayload(BaseModel):
    farmer_id: str
    unit_id: str
    crop: str
    variety: Optional[str] = None
    harvest_date_iso: Optional[str] = None
    total_weight_kg: float
    grade: Optional[str] = None
    doc_refs: Optional[List[Dict[str, Any]]] = None
    metadata: Optional[Dict[str, Any]] = None


@router.post("/farmer/traceability/batch")
def api_create_batch(req: CreateBatchPayload):
    return create_batch(
        farmer_id=req.farmer_id,
        unit_id=req.unit_id,
        crop=req.crop,
        variety=req.variety,
        harvest_date_iso=req.harvest_date_iso,
        total_weight_kg=req.total_weight_kg,
        grade=req.grade,
        doc_refs=req.doc_refs,
        metadata=req.metadata
    )


@router.get("/farmer/traceability/batch/{batch_id}")
def api_get_batch(batch_id: str):
    res = get_batch(batch_id)
    if not res:
        raise HTTPException(status_code=404, detail="batch_not_found")
    return res


@router.get("/farmer/traceability/batches/{farmer_id}")
def api_list_batches(farmer_id: str):
    return {"farmer_id": farmer_id, "batches": list_batches_for_farmer(farmer_id)}


class EventPayload(BaseModel):
    batch_id: str
    event_type: str
    actor: str
    note: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


@router.post("/farmer/traceability/event")
def api_record_event(req: EventPayload):
    res = record_event(req.batch_id, req.event_type, req.actor, note=req.note, metadata=req.metadata)
    if "error" in res:
        raise HTTPException(status_code=404, detail=res["error"])
    return res


@router.get("/farmer/traceability/events/{batch_id}")
def api_get_events(batch_id: str):
    return {"batch_id": batch_id, "events": get_batch_events(batch_id)}


class TransferPayload(BaseModel):
    batch_id: str
    from_actor: str
    to_actor: str
    note: Optional[str] = None


@router.post("/farmer/traceability/transfer")
def api_transfer(req: TransferPayload):
    res = transfer_batch(req.batch_id, req.from_actor, req.to_actor, note=req.note)
    if "error" in res:
        raise HTTPException(status_code=404, detail=res["error"])
    return res


class DocPayload(BaseModel):
    batch_id: str
    doc_ref: str
    doc_type: Optional[str] = None
    uploaded_by: Optional[str] = None


@router.post("/farmer/traceability/doc/attach")
def api_attach_doc(req: DocPayload):
    res = attach_doc_to_batch(req.batch_id, req.doc_ref, doc_type=req.doc_type, uploaded_by=req.uploaded_by)
    if "error" in res:
        raise HTTPException(status_code=404, detail=res["error"])
    return res


@router.post("/farmer/traceability/doc/detach")
def api_detach_doc(batch_id: str, doc_ref: str):
    res = detach_doc_from_batch(batch_id, doc_ref)
    if "error" in res:
        raise HTTPException(status_code=404, detail=res["error"])
    return res


@router.get("/farmer/traceability/provenance/{batch_id}")
def api_provenance(batch_id: str):
    res = provenance_report(batch_id)
    if "error" in res:
        raise HTTPException(status_code=404, detail=res["error"])
    return res


@router.get("/farmer/traceability/qr/{batch_id}")
def api_qr_payload(batch_id: str):
    res = qr_payload_for_batch(batch_id)
    if "error" in res:
        raise HTTPException(status_code=404, detail=res["error"])
    return res
