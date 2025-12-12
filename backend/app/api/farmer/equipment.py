# backend/app/api/farmer/equipment.py

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from typing import List, Optional

from app.services.farmer.equipment_service import (
    add_equipment,
    list_equipment,
    get_equipment,
    update_equipment,
    delete_equipment,
    compute_equipment_health,
    generate_maintenance_schedule,
    get_maintenance_reminders,
    get_all_maintenance_reminders,
    mark_equipment_maintenance_done,
    get_major_service_alerts,
    log_fuel_usage,
    get_fuel_usage_history,
    compute_fuel_efficiency,
    compute_breakdown_probability,
    list_high_risk_equipment,
    compute_equipment_utilization,
    compute_all_equipment_utilization,
    compute_idle_status,
    list_idle_equipment,
    assign_worker_to_equipment,
    complete_worker_operation,
    get_worker_assignments,
    list_all_worker_operations,
    compute_equipment_operating_cost,
    estimate_equipment_depreciation,
    compute_equipment_roi,
    get_equipment_suitability_score,
    recommend_equipment_for_crop,
    predict_equipment_demand,
    aggregate_weekly_equipment_demand,
    benchmark_equipment_performance,
    fleet_performance_benchmark,
    recommend_equipment_replacement,
    fleet_replacement_recommendations,
    mark_equipment_replaced,
    analyze_failure_root_cause,
    fleet_failure_root_causes,
    optimize_maintenance_schedule,
    schedule_maintenance,
    list_scheduled_maintenances,
    equipment_workload_pressure_score,
    recommend_workload_redistribution,
    scan_fleet_fuel_anomalies,
    detect_fuel_anomalies,
    analyze_equipment_cost_optimization,
    fleet_cost_optimization,
    forecast_equipment_seasonal_workload,
    benchmark_equipment_utilization,
    compute_equipment_profitability,
    fleet_profitability_ranking,
    compute_equipment_efficiency,
    recommend_efficiency_improvements,
    smart_assign_tasks,
    list_task_assignments,
    clear_task_assignment,
    fleet_downtime_forecast,
    forecast_equipment_downtime,
    fleet_downtime_forecast,
    fleet_warranty_overview,
    get_warranty_status,
    add_or_update_warranty,
)

router = APIRouter()


class AddEquipmentRequest(BaseModel):
    name: str
    type: str
    manufacturer: Optional[str] = ""
    model: Optional[str] = ""
    year: Optional[int] = None
    assigned_unit_id: Optional[int] = None


@router.post("/equipment/add")
def api_add_equipment(req: AddEquipmentRequest):
    """
    Feature #201 — Add equipment.
    """
    record = add_equipment(
        name=req.name,
        type=req.type,
        manufacturer=req.manufacturer,
        model=req.model,
        year=req.year,
        assigned_unit_id=req.assigned_unit_id,
    )
    return {"success": True, "equipment": record}


@router.get("/equipment/list")
def api_list_equipment():
    return list_equipment()


@router.get("/equipment/{equipment_id}")
def api_get_equipment(equipment_id: str):
    rec = get_equipment(equipment_id)
    if not rec:
        raise HTTPException(status_code=404, detail="equipment_not_found")
    return rec

class UpdateEquipmentRequest(BaseModel):
    name: Optional[str] = None
    type: Optional[str] = None
    manufacturer: Optional[str] = None
    model: Optional[str] = None
    year: Optional[int] = None
    assigned_unit_id: Optional[int] = None


@router.put("/equipment/update/{equipment_id}")
def api_update_equipment(equipment_id: str, req: UpdateEquipmentRequest):
    rec = update_equipment(
        equipment_id=equipment_id,
        name=req.name,
        type=req.type,
        manufacturer=req.manufacturer,
        model=req.model,
        year=req.year,
        assigned_unit_id=req.assigned_unit_id,
    )
    if not rec:
        raise HTTPException(status_code=404, detail="equipment_not_found")
    return {"success": True, "equipment": rec}

@router.delete("/equipment/delete/{equipment_id}")
def api_delete_equipment(equipment_id: str):
    deleted = delete_equipment(equipment_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="equipment_not_found")
    return {"success": True, "deleted": True, "equipment_id": equipment_id}

@router.get("/equipment/{equipment_id}/health")
def api_equipment_health(equipment_id: str):
    health = compute_equipment_health(equipment_id)
    if not health:
        raise HTTPException(status_code=404, detail="equipment_not_found")
    return health

@router.get("/equipment/{equipment_id}/maintenance/schedule")
def api_equipment_maintenance_schedule(equipment_id: str):
    schedule = generate_maintenance_schedule(equipment_id)
    if not schedule:
        raise HTTPException(status_code=404, detail="equipment_not_found")
    return schedule

@router.get("/equipment/{equipment_id}/maintenance/reminders")
def api_equipment_maintenance_reminders(equipment_id: str, days_ahead: int = 30):
    """
    Returns maintenance reminder for one equipment.
    Query param: days_ahead (default 30)
    """
    rem = get_maintenance_reminders(equipment_id, days_ahead=days_ahead)
    if rem is None:
        raise HTTPException(status_code=404, detail="equipment_not_found")
    return rem


@router.get("/equipment/maintenance/reminders")
def api_all_equipment_maintenance_reminders(days_ahead: int = 30):
    """
    Returns maintenance reminders for all equipment.
    Query param: days_ahead (default 30)
    """
    return get_all_maintenance_reminders(days_ahead=days_ahead)

class MarkMaintenanceRequest(BaseModel):
    performed_at: Optional[str] = None
    notes: Optional[str] = ""


@router.post("/equipment/{equipment_id}/maintenance/mark-done")
def api_mark_maintenance_done(equipment_id: str, req: MarkMaintenanceRequest):
    performed_at = None
    if req.performed_at:
        performed_at = datetime.fromisoformat(req.performed_at)

    result = mark_equipment_maintenance_done(
        equipment_id=equipment_id,
        performed_at=performed_at,
        notes=req.notes,
    )

    if not result:
        raise HTTPException(status_code=404, detail="equipment_not_found")

    return {"success": True, "data": result}

@router.get("/equipment/{equipment_id}/service/major-alerts")
def api_major_service_alerts(equipment_id: str):
    alerts = get_major_service_alerts(equipment_id)
    if not alerts:
        raise HTTPException(status_code=404, detail="equipment_not_found")
    return alerts

class LogFuelRequest(BaseModel):
    liters: float
    cost: float = 0.0
    usage_hours: float = 0.0
    filled_at: Optional[str] = None


@router.post("/equipment/{equipment_id}/fuel/log")
def api_log_fuel_usage(equipment_id: str, req: LogFuelRequest):
    filled_at = None
    if req.filled_at:
        filled_at = datetime.fromisoformat(req.filled_at)

    entry = log_fuel_usage(
        equipment_id=equipment_id,
        liters=req.liters,
        cost=req.cost,
        usage_hours=req.usage_hours,
        filled_at=filled_at,
    )

    if not entry:
        raise HTTPException(status_code=404, detail="equipment_not_found")

    return {"success": True, "entry": entry}


@router.get("/equipment/{equipment_id}/fuel/history")
def api_fuel_history(equipment_id: str):
    history = get_fuel_usage_history(equipment_id)
    if not history:
        raise HTTPException(status_code=404, detail="equipment_not_found")
    return history


@router.get("/equipment/{equipment_id}/fuel/efficiency")
def api_fuel_efficiency(equipment_id: str):
    efficiency = compute_fuel_efficiency(equipment_id)
    if not efficiency:
        raise HTTPException(status_code=404, detail="equipment_not_found")
    return efficiency

@router.get("/equipment/{equipment_id}/breakdown-risk")
def api_equipment_breakdown_risk(equipment_id: str):
    res = compute_breakdown_probability(equipment_id)
    if not res:
        raise HTTPException(status_code=404, detail="equipment_not_found")
    return res

@router.get("/equipment/high-risk")
def api_list_high_risk_equipment(threshold: int = 60):
    """
    Returns all equipment with breakdown_probability >= threshold.
    Default threshold = 60.
    """
    res = list_high_risk_equipment(threshold)
    return res

@router.get("/equipment/{equipment_id}/utilization")
def api_equipment_utilization(equipment_id: str):
    result = compute_equipment_utilization(equipment_id)
    if not result:
        raise HTTPException(status_code=404, detail="equipment_not_found")
    return result


@router.get("/equipment/utilization/summary")
def api_equipment_utilization_summary():
    return compute_all_equipment_utilization()

@router.get("/equipment/{equipment_id}/idle-status")
def api_idle_status(equipment_id: str):
    info = compute_idle_status(equipment_id)
    if not info:
        raise HTTPException(status_code=404, detail="equipment_not_found")
    return info


@router.get("/equipment/idle")
def api_idle_equipment(min_idle_days: int = 7):
    return list_idle_equipment(min_idle_days=min_idle_days)

class WorkerAssignRequest(BaseModel):
    worker_id: str
    start_time: Optional[str] = None
    notes: Optional[str] = ""


@router.post("/equipment/{equipment_id}/worker/assign")
def api_assign_worker(equipment_id: str, req: WorkerAssignRequest):
    start = None
    if req.start_time:
        start = datetime.fromisoformat(req.start_time)

    entry = assign_worker_to_equipment(
        worker_id=req.worker_id,
        equipment_id=equipment_id,
        start_time=start,
        notes=req.notes,
    )

    if not entry:
        raise HTTPException(status_code=404, detail="equipment_not_found")

    return {"success": True, "assignment": entry}


class WorkerCompleteRequest(BaseModel):
    worker_id: str
    end_time: Optional[str] = None


@router.post("/equipment/{equipment_id}/worker/complete")
def api_complete_worker_operation(equipment_id: str, req: WorkerCompleteRequest):
    end = None
    if req.end_time:
        end = datetime.fromisoformat(req.end_time)

    entry = complete_worker_operation(
        worker_id=req.worker_id,
        equipment_id=equipment_id,
        end_time=end
    )

    if not entry:
        raise HTTPException(status_code=404, detail="operation_not_found")

    return {"success": True, "operation": entry}


@router.get("/equipment/{equipment_id}/worker/assignments")
def api_worker_assignments(equipment_id: str):
    return get_worker_assignments(equipment_id)


@router.get("/equipment/worker/operations/all")
def api_all_worker_operations():
    return list_all_worker_operations()

@router.get("/equipment/{equipment_id}/cost/summary")
def api_equipment_cost_summary(equipment_id: str):
    res = compute_equipment_operating_cost(equipment_id)
    if not res:
        raise HTTPException(status_code=404, detail="equipment_not_found")
    return res


@router.get("/equipment/{equipment_id}/depreciation")
def api_equipment_depreciation(equipment_id: str, years: int = 5, method: str = "straight_line"):
    res = estimate_equipment_depreciation(equipment_id, years=years, method=method)
    if not res:
        raise HTTPException(status_code=404, detail="equipment_not_found")
    return res


@router.get("/equipment/{equipment_id}/roi")
def api_equipment_roi(equipment_id: str, analysis_period_years: int = 1):
    res = compute_equipment_roi(equipment_id, analysis_period_years=analysis_period_years)
    if not res:
        raise HTTPException(status_code=404, detail="equipment_not_found")
    return res

@router.get("/equipment/{equipment_id}/suitability/{crop}/{stage}")
def api_equipment_suitability(equipment_id: str, crop: str, stage: str):
    res = get_equipment_suitability_score(equipment_id, crop, stage)
    if not res:
        raise HTTPException(status_code=404, detail="equipment_not_found")
    return res


@router.get("/equipment/recommendations/crop")
def api_recommend_equipment_for_crop(crop: str, stage: str):
    return recommend_equipment_for_crop(crop, stage)

class UnitPlanItem(BaseModel):
    unit_id: str
    crop: str
    start_date: Optional[str] = None
    stages: Optional[List[str]] = None
    stage_start_overrides: Optional[dict] = None


@router.post("/equipment/predict-demand")
def api_predict_equipment_demand(unit_plans: List[UnitPlanItem], horizon_days: int = 90):
    """
    Predict equipment demand over the next `horizon_days` based on provided unit plans.
    Request body (unit_plans): list of { unit_id, crop, start_date (YYYY-MM-DD), stages (optional) }
    """
    # Convert pydantic UnitPlanItem objects to plain dicts for service function
    plans = []
    for item in unit_plans:
        plans.append(item.dict())

    result = predict_equipment_demand(plans, horizon_days=horizon_days)
    return result


@router.get("/equipment/demand/summary")
def api_equipment_demand_summary(horizon_days: int = 90):
    """
    Convenience endpoint: if farmer hasn't provided plans, we attempt to infer from current unit details:
    - Scan units from unit_service if available (best-effort)
    - Otherwise returns an empty plan skeleton
    """
    # Try to gather unit plans from unit_service (best-effort)
    plans = []
    try:
        from app.services.farmer.unit_service import list_units  # this function may differ in your codebase
        units = list_units().get("items", [])
        for u in units:
            # best-effort: unit should contain 'next_stage_start' or 'crop' fields else default to today
            crop = u.get("crop", "generic")
            start_date = u.get("next_stage_start") or u.get("planted_at") or datetime.utcnow().date().isoformat()
            plans.append({"unit_id": str(u.get("id", u.get("unit_id", "unknown"))), "crop": crop, "start_date": start_date})
    except Exception:
        # fall back to empty
        plans = []

    return predict_equipment_demand(plans, horizon_days=horizon_days)

class UnitPlanWeekly(BaseModel):
    unit_id: str
    crop: str
    start_date: Optional[str] = None
    stages: Optional[List[str]] = None
    stage_start_overrides: Optional[dict] = None


@router.post("/equipment/predict-demand/weekly")
def api_predict_weekly_equipment_demand(unit_plans: List[UnitPlanWeekly], horizon_days: int = 90):
    """
    Returns weekly aggregated equipment demand.
    Perfect for calendar or dashboard usage.
    """

    plans = [p.dict() for p in unit_plans]

    demand = predict_equipment_demand(plans, horizon_days=horizon_days)
    weekly = aggregate_weekly_equipment_demand(demand.get("date_equipment_map", {}))

    return {
        "horizon_start": demand.get("horizon_start"),
        "horizon_end": demand.get("horizon_end"),
        "horizon_days": demand.get("horizon_days"),
        "weekly_demand": weekly,
        "generated_at": datetime.utcnow().isoformat()
    }

@router.get("/equipment/{equipment_id}/performance")
def api_equipment_performance(equipment_id: str):
    result = benchmark_equipment_performance(equipment_id)
    if not result:
        raise HTTPException(status_code=404, detail="equipment_not_found")
    return result


@router.get("/equipment/performance/fleet")
def api_fleet_performance():
    return fleet_performance_benchmark()

@router.get("/equipment/{equipment_id}/replacement")
def api_equipment_replacement(equipment_id: str):
    res = recommend_equipment_replacement(equipment_id)
    if not res:
        raise HTTPException(status_code=404, detail="equipment_not_found")
    return res


@router.get("/equipment/replacement/fleet")
def api_fleet_replacement(threshold_urgency: str = "medium"):
    return fleet_replacement_recommendations(threshold_urgency=threshold_urgency)


class ReplaceEquipmentRequest(BaseModel):
    replaced_by_equipment_id: Optional[str] = None
    notes: Optional[str] = None


@router.post("/equipment/{equipment_id}/replace")
def api_mark_equipment_replaced(equipment_id: str, req: ReplaceEquipmentRequest):
    res = mark_equipment_replaced(
        equipment_id=equipment_id,
        replaced_by_equipment_id=req.replaced_by_equipment_id,
        notes=req.notes
    )
    if "error" in res:
        raise HTTPException(status_code=404, detail=res["error"])
    return res

@router.get("/equipment/{equipment_id}/failure-rca")
def api_failure_rca(equipment_id: str):
    result = analyze_failure_root_cause(equipment_id)
    if not result:
        raise HTTPException(status_code=404, detail="equipment_not_found")
    return result


@router.get("/equipment/failure-rca/fleet")
def api_fleet_failure_rca():
    return fleet_failure_root_causes()

class OptimizeMaintenanceRequest(BaseModel):
    horizon_days: Optional[int] = 60
    avoid_peak: Optional[bool] = True
    min_window_days: Optional[int] = 1
    unit_plans: Optional[List[dict]] = None


@router.post("/equipment/{equipment_id}/maintenance/optimize")
def api_optimize_maintenance(equipment_id: str, req: OptimizeMaintenanceRequest):
    res = optimize_maintenance_schedule(
        equipment_id=equipment_id,
        horizon_days=req.horizon_days,
        avoid_peak=req.avoid_peak,
        unit_plans=req.unit_plans,
        min_window_days=req.min_window_days
    )
    if res is None:
        raise HTTPException(status_code=404, detail="equipment_not_found")
    return res


class ScheduleMaintenanceRequest(BaseModel):
    start_date_iso: str  # ISO datetime string
    duration_days: Optional[int] = 1
    notes: Optional[str] = ""


@router.post("/equipment/{equipment_id}/maintenance/schedule")
def api_schedule_maintenance(equipment_id: str, req: ScheduleMaintenanceRequest):
    res = schedule_maintenance(
        equipment_id=equipment_id,
        start_date_iso=req.start_date_iso,
        duration_days=req.duration_days,
        notes=req.notes
    )
    if not res or "error" in res:
        raise HTTPException(status_code=400, detail=res)
    return {"success": True, "scheduled": res}


@router.get("/equipment/{equipment_id}/maintenance/scheduled")
def api_list_equipment_schedules(equipment_id: str):
    return list_scheduled_maintenances(equipment_id=equipment_id)


@router.get("/equipment/maintenance/scheduled")
def api_list_all_schedules():
    return list_scheduled_maintenances()

@router.get("/equipment/{equipment_id}/workload-pressure")
def api_workload_pressure(equipment_id: str):
    res = equipment_workload_pressure_score(equipment_id)
    if not res:
        raise HTTPException(status_code=404, detail="equipment_not_found")
    return res


@router.get("/equipment/workload/redistribute")
def api_workload_redistribute(horizon_days: int = 7):
    return recommend_workload_redistribution(horizon_days=horizon_days)

@router.get("/equipment/{equipment_id}/fuel/anomalies")
def api_equipment_fuel_anomalies(equipment_id: str, lookback_days: int = 30):
    res = detect_fuel_anomalies(equipment_id, lookback_days=lookback_days)
    if res is None:
        raise HTTPException(status_code=404, detail="equipment_not_found")
    return res


@router.get("/equipment/fuel/anomalies")
def api_fleet_fuel_anomalies(lookback_days: int = 30):
    return scan_fleet_fuel_anomalies(lookback_days=lookback_days)

@router.get("/equipment/{equipment_id}/cost-optimization")
def api_equipment_cost_optimization(equipment_id: str):
    r = analyze_equipment_cost_optimization(equipment_id)
    if not r:
        raise HTTPException(status_code=404, detail="equipment_not_found")
    return r


@router.get("/equipment/cost-optimization/fleet")
def api_fleet_cost_optimization():
    return fleet_cost_optimization()

class SeasonalWorkloadRequest(BaseModel):
    unit_plans: List[dict]
    season_months: Optional[int] = 6
    include_weather: Optional[bool] = True


@router.post("/equipment/workload/seasonal")
def api_seasonal_workload(req: SeasonalWorkloadRequest):
    result = forecast_equipment_seasonal_workload(
        unit_plans=req.unit_plans,
        season_months=req.season_months,
        include_weather=req.include_weather
    )
    return result

class UnitPlanPayload(BaseModel):
    unit_plans: List[dict]


@router.post("/equipment/{equipment_id}/profitability")
def api_equipment_profitability(equipment_id: str, req: UnitPlanPayload):
    res = compute_equipment_profitability(equipment_id, req.unit_plans)
    if not res:
        raise HTTPException(status_code=404, detail="equipment_not_found")
    return res


@router.post("/equipment/profitability/ranking")
def api_fleet_profitability(req: UnitPlanPayload):
    return fleet_profitability_ranking(req.unit_plans)

class TaskItem(BaseModel):
    task_id: Optional[str] = None
    required_equipment_type: str
    start_iso: str
    end_iso: Optional[str] = None
    estimated_hours: Optional[float] = None
    priority: Optional[int] = 5
    crop: Optional[str] = None
    stage: Optional[str] = None
    unit_id: Optional[str] = None
    preferred_equipment_ids: Optional[List[str]] = None


class AssignTasksRequest(BaseModel):
    tasks: List[TaskItem]
    auto_confirm: Optional[bool] = False


@router.post("/equipment/assign-tasks")
def api_assign_tasks(req: AssignTasksRequest):
    tasks = [t.dict() for t in req.tasks]
    res = smart_assign_tasks(tasks, auto_confirm=req.auto_confirm)
    return res


@router.get("/equipment/assignments")
def api_list_assignments(task_id: Optional[str] = None):
    return list_task_assignments(task_id=task_id)


@router.post("/equipment/assignments/{task_id}/cancel")
def api_cancel_assignment(task_id: str):
    res = clear_task_assignment(task_id)
    if "error" in res:
        raise HTTPException(status_code=404, detail=res["error"])
    return res

@router.get("/equipment/{equipment_id}/downtime-forecast")
def api_equipment_downtime(equipment_id: str, horizon_days: int = 30):
    r = forecast_equipment_downtime(equipment_id, horizon_days)
    if not r:
        raise HTTPException(status_code=404, detail="equipment_not_found")
    return r


@router.get("/equipment/downtime-forecast/fleet")
def api_fleet_downtime(horizon_days: int = 30):
    return fleet_downtime_forecast(horizon_days)

class WarrantyPayload(BaseModel):
    equipment_id: str
    start_date: str
    end_date: str
    provider: Optional[str] = "Unknown"
    notes: Optional[str] = None


@router.post("/equipment/warranty")
def api_add_warranty(req: WarrantyPayload):
    rec = add_or_update_warranty(
        req.equipment_id,
        req.start_date,
        req.end_date,
        provider=req.provider,
        notes=req.notes
    )
    return {"success": True, "warranty": rec}


@router.get("/equipment/{equipment_id}/warranty")
def api_get_warranty(equipment_id: str):
    return get_warranty_status(equipment_id)


@router.get("/equipment/warranty/fleet")
def api_fleet_warranty():
    return fleet_warranty_overview()
