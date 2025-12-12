# backend/app/api/farmer/batch.py

from fastapi import APIRouter
from typing import List

from app.services.farmer.batch_intel_runner import (
    run_intelligence_for_units,
    simulate_long_running_batch,
)

router = APIRouter()


@router.post("/batch/intelligence")
def api_batch_intelligence(unit_ids: List[int], stage: str, crop: str = "generic"):
    """
    Computes unified intelligence for multiple units in one request.
    """
    return run_intelligence_for_units(unit_ids, stage, crop)


@router.post("/batch/intelligence/simulated")
def api_batch_simulated(unit_ids: List[int], stage: str):
    """
    Simulates long-running batch job execution.
    """
    return simulate_long_running_batch(unit_ids, stage)
