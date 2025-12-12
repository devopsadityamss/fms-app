# backend/app/services/farmer/input_forecasting_service.py

from datetime import datetime
from typing import Dict, Any, List, Optional

# We reuse production unit, crop, stage templates, and operations
# Adjust imports if your folder structure differs:
from app.services.farmer.unit_service import _unit_store
from app.services.farmer.stage_service import _stage_template_store
from app.services.farmer.task_service import _task_templates_store


"""
This service forecasts total inputs needed for a production unit across:
- seed requirement
- fertilizer requirement (N/P/K or custom)
- pesticide requirement
- irrigation requirement (liters or hours)
- stage-wise breakdown
- recommended procurement timeline
"""


# --------------------------
# Helper: Safe Parse Float
# --------------------------
def _safe_float(v, default=0.0):
    try:
        return float(v)
    except Exception:
        return default


# --------------------------
# Core mechanism
# --------------------------
def forecast_inputs_for_unit(unit_id: str) -> Dict[str, Any]:
    """
    Calculate crop input needs for the complete crop cycle of a unit.
    Returns detailed breakdown.
    """

    unit = _unit_store.get(unit_id)
    if not unit:
        return {"status": "unit_not_found", "unit_id": unit_id}

    crop = unit.get("crop")
    area = _safe_float(unit.get("area", 1))  # fallback 1 acre
    template_id = unit.get("stage_template_id")

    # Load template (list of stages)
    template = _stage_template_store.get(template_id, {})
    stages = template.get("stages", [])

    results = {
        "unit_id": unit_id,
        "crop": crop,
        "area": area,
        "stage_count": len(stages),
        "stages": [],
        "total_inputs": {
            "seed_kg": 0,
            "fertilizer": {},   # dynamic N/P/K or custom
            "pesticide_liters": 0,
            "irrigation_liters": 0
        },
        "recommended_procurement": [],
        "generated_at": datetime.utcnow().isoformat()
    }

    fertilizer_totals = {}

    # --------------------------
    # Iterate through stages
    # --------------------------
    for stage in stages:
        stage_name = stage.get("name")
        operations = stage.get("operations", [])

        stage_inputs = {
            "stage_name": stage_name,
            "seed_kg": 0,
            "fertilizer": {},
            "pesticide_liters": 0,
            "irrigation_liters": 0,
            "tasks": []
        }

        # --------------------------
        # Loop through operations
        # --------------------------
        for op_id in operations:
            task_def = _task_templates_store.get(op_id, {})
            op_type = task_def.get("type")
            op_inputs = task_def.get("inputs", {}) or {}

            seed_rate = _safe_float(op_inputs.get("seed_rate_kg_per_acre"))
            fert = op_inputs.get("fertilizer", {})
            pesticide_lph = _safe_float(op_inputs.get("pesticide_liters_per_acre"))
            irrigation_lph = _safe_float(op_inputs.get("irrigation_liters_per_acre"))

            # -------------- Input estimation --------------
            # Seed:
            if seed_rate:
                seed_amt = seed_rate * area
                stage_inputs["seed_kg"] += seed_amt
                results["total_inputs"]["seed_kg"] += seed_amt

            # Fertilizer:
            if isinstance(fert, dict):
                for k, v in fert.items():  # k = nutrient, v = kg_per_acre
                    val = _safe_float(v) * area
                    stage_inputs["fertilizer"][k] = stage_inputs["fertilizer"].get(k, 0) + val
                    fertilizer_totals[k] = fertilizer_totals.get(k, 0) + val

            # Pesticide:
            if pesticide_lph:
                lit = pesticide_lph * area
                stage_inputs["pesticide_liters"] += lit
                results["total_inputs"]["pesticide_liters"] += lit

            # Irrigation:
            if irrigation_lph:
                lit = irrigation_lph * area
                stage_inputs["irrigation_liters"] += lit
                results["total_inputs"]["irrigation_liters"] += lit

            # Record task
            stage_inputs["tasks"].append({
                "task_id": op_id,
                "task_name": task_def.get("name"),
                "operation_type": op_type,
                "inputs": op_inputs
            })

        # Append stage summary
        results["stages"].append(stage_inputs)

    # Store fertilizer totals
    results["total_inputs"]["fertilizer"] = {k: round(v, 2) for k, v in fertilizer_totals.items()}

    # --------------------------
    # Build procurement list
    # --------------------------
    # Seeds should be purchased before sowing stage
    sow_stage = None
    for st in results["stages"]:
        if st["seed_kg"] > 0:
            sow_stage = st
            break

    if sow_stage:
        results["recommended_procurement"].append({
            "item": "Seed",
            "quantity": round(results["total_inputs"]["seed_kg"], 2),
            "stage_needed": sow_stage["stage_name"],
            "urgency": "before_sowing"
        })

    # Fertilizers
    for nutrient, qty in fertilizer_totals.items():
        results["recommended_procurement"].append({
            "item": f"Fertilizer_{nutrient}",
            "quantity": round(qty, 2),
            "stage_needed": "multi_stage",
            "urgency": "spread_across_stages"
        })

    # Pesticides
    if results["total_inputs"]["pesticide_liters"] > 0:
        results["recommended_procurement"].append({
            "item": "Pesticides",
            "quantity": round(results["total_inputs"]["pesticide_liters"], 2),
            "urgency": "stage_wise_sprays"
        })

    # Irrigation
    if results["total_inputs"]["irrigation_liters"] > 0:
        results["recommended_procurement"].append({
            "item": "Irrigation Water Requirement",
            "quantity": round(results["total_inputs"]["irrigation_liters"], 2),
            "urgency": "stage_wise_irrigation"
        })

    return results
