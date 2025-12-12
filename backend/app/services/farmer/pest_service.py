# backend/app/services/farmer/pest_service.py

from datetime import datetime
from typing import Dict, Any, List

# Simple pattern-based pest/disease stub (no ML). Returns mock risk and recommended actions.

def scan_basic_pest_risks(unit_id: int, stage_name: str, weather: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Return list of possible pest/disease risks based on stage & weather heuristics."""
    risks = []
    temp = weather.get("temperature", 28)
    humidity = weather.get("humidity", 60)

    if stage_name.lower() in ["vegetative", "flowering"] and temp > 30 and humidity > 70:
        risks.append({
            "name": "Fungal Infection Risk",
            "severity": "high",
            "recommendation": "Apply recommended fungicide or organic spray; increase monitoring frequency.",
            "timestamp": datetime.utcnow(),
        })

    if stage_name.lower() == "vegetative" and temp > 28:
        risks.append({
            "name": "Aphid/Whitefly Risk",
            "severity": "medium",
            "recommendation": "Inspect undersides of leaves; use sticky traps or neem spray.",
            "timestamp": datetime.utcnow(),
        })

    return risks


def get_pest_intel(unit_id: int, stage_name: str, weather: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "unit_id": unit_id,
        "timestamp": datetime.utcnow(),
        "risks": scan_basic_pest_risks(unit_id, stage_name, weather),
        "summary_count": len(scan_basic_pest_risks(unit_id, stage_name, weather))
    }
