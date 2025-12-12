# backend/app/services/farmer/sustainability_service.py

from datetime import datetime
from typing import Dict, Any

# Mock sustainability scoring: water efficiency, fertilizer efficiency, biodiversity proxy.

def compute_sustainability_score(unit_id: int, water_usage_efficiency: float = 0.7, fertilizer_efficiency: float = 0.6) -> Dict[str, Any]:
    """
    Returns a score (0-100) and breakdown.
    """
    base = (water_usage_efficiency * 50) + (fertilizer_efficiency * 40)
    biodiversity = 10  # mock
    score = min(100, int(base + biodiversity))
    return {
        "unit_id": unit_id,
        "timestamp": datetime.utcnow(),
        "score": score,
        "breakdown": {
            "water_efficiency": water_usage_efficiency,
            "fertilizer_efficiency": fertilizer_efficiency,
            "biodiversity_index": biodiversity
        }
    }

def get_sustainability_summary(unit_id: int) -> Dict[str, Any]:
    """Unified sustainability intel."""
    return compute_sustainability_score(unit_id)
