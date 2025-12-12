from fastapi import APIRouter, Body, HTTPException
from typing import Dict, Any

from app.services.farmer.input_batch_service import (
    add_input_batch, list_input_batches, get_input_batch,
    update_input_batch, delete_input_batch,
    record_usage, list_usage_logs,
    check_batch_status, batch_summary,
    farmer_inventory_overview
)

router = APIRouter()

# --------------------------
# CRUD
# --------------------------
@router.post("/inputs/batch")
def api_add_batch(payload: Dict[str, Any] = Body(...)):
    return add_input_batch(**payload)


@router.get("/inputs/batch/{batch_id}")
def api_get_batch(batch_id: str):
    res = get_input_batch(batch_id)
    if not res:
        raise HTTPException(404, "batch_not_found")
    return res


@router.get("/inputs/{farmer_id}/batches")
def api_list_batches(farmer_id: str):
    return list_input_batches(farmer_id)


@router.put("/inputs/batch/{batch_id}")
def api_update_batch(batch_id: str, payload: Dict[str, Any] = Body(...)):
    return update_input_batch(batch_id, payload)


@router.delete("/inputs/batch/{batch_id}")
def api_delete_batch(batch_id: str):
    return delete_input_batch(batch_id)


# --------------------------
# USAGE LOGGING
# --------------------------
@router.post("/inputs/batch/{batch_id}/use")
def api_record_usage(batch_id: str, payload: Dict[str, Any] = Body(...)):
    return record_usage(batch_id, **payload)


@router.get("/inputs/batch/{batch_id}/logs")
def api_usage_logs(batch_id: str):
    return list_usage_logs(batch_id)


# --------------------------
# STATUS / SUMMARY
# --------------------------
@router.get("/inputs/batch/{batch_id}/status")
def api_status(batch_id: str):
    return check_batch_status(batch_id)


@router.get("/inputs/batch/{batch_id}/summary")
def api_summary(batch_id: str):
    return batch_summary(batch_id)


@router.get("/inputs/{farmer_id}/inventory")
def api_inventory(farmer_id: str):
    return farmer_inventory_overview(farmer_id)
# ==========================================================
# INPUT INTELLIGENCE API (Features 328–330)
# ==========================================================

from app.services.farmer.input_batch_service import (
    scan_expired_batches,
    detect_input_contamination_risk,
    farmer_contamination_overview,
    recommend_best_batch,
    input_intelligence_summary
)

# --------------------------
# EXPIRY / NEAR-EXPIRY SCAN
# --------------------------
@router.get("/inputs/{farmer_id}/expiry-scan")
def api_expiry_scan(farmer_id: str, days_before: int = 15):
    """
    Lists expired and near-expiry batches.
    """
    return scan_expired_batches(farmer_id, days_before)


# --------------------------
# CONTAMINATION RISK
# --------------------------
@router.get("/inputs/batch/{batch_id}/contamination-risk")
def api_batch_contamination(batch_id: str):
    """
    Detects if a batch has unsafe combinations in name/composition.
    """
    return detect_input_contamination_risk(batch_id)


@router.get("/inputs/{farmer_id}/contamination-overview")
def api_contamination_overview(farmer_id: str):
    """
    Lists all contamination risks across farmer inventory.
    """
    return farmer_contamination_overview(farmer_id)


# --------------------------
# USAGE OPTIMIZER
# --------------------------
@router.get("/inputs/{farmer_id}/recommend")
def api_recommend_batch(
    farmer_id: str,
    input_type: str,
    priority: str = "expiry"
):
    """
    Recommends the best batch to use next.
    priority: expiry | stock | oldest | best_quality
    """
    return recommend_best_batch(farmer_id, input_type, priority)


# --------------------------
# FULL INTELLIGENCE SUMMARY
# --------------------------
@router.get("/inputs/{farmer_id}/intelligence-summary")
def api_input_intelligence(farmer_id: str):
    """
    Provides:
      - expiry scan
      - contamination risks
      - recommended strategies
    """
    return input_intelligence_summary(farmer_id)
