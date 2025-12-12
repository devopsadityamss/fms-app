# backend/app/services/farmer/batch_intel_runner.py

"""
Batch Intelligence Runner

Purpose:
- Run intelligence for multiple production units in batch mode.
- Prepare backend for scheduled or cron-like execution.
- Provide mock long-running job simulation.
- No DB functionality included (mock-only).

This is a helper layer for:
- dashboards needing multi-unit summaries
- farm administrators needing aggregated intelligence
- future asynchronous processing frameworks
"""

from datetime import datetime
from typing import Dict, Any, List

from app.services.farmer.intelligence_engine_service import get_full_intelligence


def run_intelligence_for_units(unit_ids: List[int], stage: str, crop: str = "generic") -> Dict[str, Any]:
    """
    Runs unified intelligence engine for each unit ID sequentially.
    """
    results = {}
    for uid in unit_ids:
        try:
            bundle = get_full_intelligence(
                unit_id=uid,
                stage=stage,
                current_stock={},
                crop=crop
            )
            results[uid] = {"success": True, "data": bundle}
        except Exception as e:
            results[uid] = {"success": False, "error": str(e)}

    return {
        "timestamp": datetime.utcnow(),
        "unit_count": len(unit_ids),
        "results": results,
    }


def simulate_long_running_batch(unit_ids: List[int], stage: str) -> Dict[str, Any]:
    """
    Mock simulation of a long batch job (no real delay).
    In production this would involve async worker queues.
    """
    start_time = datetime.utcnow()

    # Run intelligence (synchronously here)
    output = run_intelligence_for_units(unit_ids, stage)

    end_time = datetime.utcnow()
    duration = (end_time - start_time).total_seconds()

    return {
        "timestamp": end_time,
        "duration_seconds": duration,
        "unit_count": len(unit_ids),
        "batch_output": output,
    }
