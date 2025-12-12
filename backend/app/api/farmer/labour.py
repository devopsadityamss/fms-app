# backend/app/api/farmer/labour.py

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict, Any

from app.services.farmer.labour_service import (
    # registration
    add_laborer, register_worker, get_worker, list_laborers, update_worker, deactivate_worker,
    # availability
    set_availability, list_availability,
    # logs
    record_labor_hours, list_labor_logs,
    # tasks
    assign_task_to_labor, list_assignments, list_tasks, update_task_status, auto_assign, list_assignments_for_worker, list_open_tasks_for_farmer,
    # timesheets/payroll
    clock_in, clock_out, list_timesheets, compute_payroll_for_worker,
    # estimation/reports
    estimate_labor_required, detect_labor_shortage, labor_efficiency_score, labor_summary, find_available_workers
)

router = APIRouter()

# ---------------------
# Pydantic payloads
# ---------------------
class AddLaborerPayload(BaseModel):
    farmer_id: str
    name: str
    labor_type: str
    daily_wage: Optional[float] = None
    skills: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None

class RegisterWorkerPayload(BaseModel):
    name: str
    contact: Optional[str] = None
    skill_tags: Optional[List[str]] = None
    hourly_rate: Optional[float] = 100.0
    farmer_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

class AvailabilityPayload(BaseModel):
    laborer_id: str
    date_iso: str
    from_time_iso: Optional[str] = None
    to_time_iso: Optional[str] = None
    note: Optional[str] = None

class LaborLogPayload(BaseModel):
    laborer_id: str
    unit_id: str
    task_name: str
    hours: float
    cost: Optional[float] = None
    date_iso: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

class AssignPayload(BaseModel):
    farmer_id: str
    unit_id: str
    laborer_id: str
    task_name: str
    estimated_hours: float
    due_date_iso: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

class ClockInPayload(BaseModel):
    worker_id: str
    task_id: Optional[str] = None
    ts_iso: Optional[str] = None

class ClockOutPayload(BaseModel):
    worker_id: str
    timesheet_id: str
    ts_iso: Optional[str] = None

# ---------------------
# Registration
# ---------------------
@router.post("/farmer/labour/laborer")
def api_add_laborer(req: AddLaborerPayload):
    return add_laborer(req.farmer_id, req.name, req.labor_type, daily_wage=req.daily_wage, skills=req.skills, metadata=req.metadata)

@router.post("/farmer/labour/worker")
def api_register_worker(req: RegisterWorkerPayload):
    return register_worker(req.name, contact=req.contact, skill_tags=req.skill_tags, hourly_rate=req.hourly_rate, farmer_id=req.farmer_id, metadata=req.metadata)

@router.get("/farmer/labour/worker/{worker_id}")
def api_get_worker(worker_id: str):
    res = get_worker(worker_id)
    if not res:
        raise HTTPException(status_code=404, detail="worker_not_found")
    return res

@router.get("/farmer/labour/workers")
def api_list_laborers(farmer_id: Optional[str] = None, skill_tags: Optional[str] = None, active_only: Optional[bool] = True):
    tags = skill_tags.split(",") if skill_tags else None
    return {"workers": list_laborers(farmer_id=farmer_id, skill_tags=tags, active_only=bool(active_only))}

@router.post("/farmer/labour/worker/{worker_id}")
def api_update_worker(worker_id: str, updates: Dict[str, Any]):
    res = update_worker(worker_id, updates)
    if "error" in res:
        raise HTTPException(status_code=404, detail=res["error"])
    return res

@router.post("/farmer/labour/worker/{worker_id}/deactivate")
def api_deactivate_worker(worker_id: str):
    return deactivate_worker(worker_id)

# ---------------------
# Availability
# ---------------------
@router.post("/farmer/labour/availability")
def api_set_availability(req: AvailabilityPayload):
    res = set_availability(req.laborer_id, req.date_iso, req.from_time_iso, req.to_time_iso, note=req.note)
    if "error" in res:
        raise HTTPException(status_code=400, detail=res["error"])
    return res

@router.get("/farmer/labour/availability/{laborer_id}")
def api_list_availability(laborer_id: str, from_date_iso: Optional[str] = None, to_date_iso: Optional[str] = None):
    return {"availability": list_availability(laborer_id, from_date_iso, to_date_iso)}

# ---------------------
# Logs
# ---------------------
@router.post("/farmer/labour/log")
def api_record_log(req: LaborLogPayload):
    return record_labor_hours(req.laborer_id, req.unit_id, req.task_name, req.hours, cost=req.cost, date_iso=req.date_iso, metadata=req.metadata)

@router.get("/farmer/labour/logs/{unit_id}")
def api_list_logs(unit_id: str):
    return {"unit_id": unit_id, "logs": list_labor_logs(unit_id)}

# ---------------------
# Tasks & Assignments
# ---------------------
@router.post("/farmer/labour/assign")
def api_assign(req: AssignPayload):
    res = assign_task_to_labor(req.farmer_id, req.unit_id, req.laborer_id, req.task_name, req.estimated_hours, due_date_iso=req.due_date_iso, metadata=req.metadata)
    if "error" in res:
        raise HTTPException(status_code=400, detail=res["error"])
    return res

@router.get("/farmer/labour/assignments/{unit_id}")
def api_list_assignments(unit_id: str):
    return {"assignments": list_assignments(unit_id)}

@router.get("/farmer/labour/tasks")
def api_list_tasks(farmer_id: Optional[str] = None, status: Optional[str] = None):
    return {"tasks": list_tasks(farmer_id=farmer_id, status=status)}

@router.post("/farmer/labour/task/{task_id}/status")
def api_update_task_status(task_id: str, body: Dict[str, Any]):
    status = body.get("status")
    if not status:
        raise HTTPException(status_code=400, detail="missing_status")
    res = update_task_status(task_id, status)
    if "error" in res:
        raise HTTPException(status_code=400, detail=res["error"])
    return res

@router.post("/farmer/labour/auto_assign/{assignment_id}")
def api_auto_assign(assignment_id: str):
    res = auto_assign(assignment_id)
    if "error" in res:
        raise HTTPException(status_code=400, detail=res["error"])
    return res

@router.get("/farmer/labour/assignments/worker/{worker_id}")
def api_assignments_for_worker(worker_id: str):
    return {"assignments": list_assignments_for_worker(worker_id)}

@router.get("/farmer/labour/open_tasks/{farmer_id}")
def api_open_tasks(farmer_id: str):
    return {"open_tasks": list_open_tasks_for_farmer(farmer_id)}

# ---------------------
# Timesheets & Payroll
# ---------------------
@router.post("/farmer/labour/clock_in")
def api_clock_in(req: ClockInPayload):
    res = clock_in(req.worker_id, req.task_id, ts_iso=req.ts_iso)
    if "error" in res:
        raise HTTPException(status_code=400, detail=res["error"])
    return res

@router.post("/farmer/labour/clock_out")
def api_clock_out(req: ClockOutPayload):
    res = clock_out(req.worker_id, req.timesheet_id, ts_iso=req.ts_iso)
    if "error" in res:
        raise HTTPException(status_code=400, detail=res["error"])
    return res

@router.get("/farmer/labour/timesheets/{worker_id}")
def api_list_timesheets(worker_id: str, from_date_iso: Optional[str] = None, to_date_iso: Optional[str] = None):
    return {"timesheets": list_timesheets(worker_id, from_date_iso, to_date_iso)}

@router.get("/farmer/labour/payroll/{worker_id}")
def api_payroll(worker_id: str, from_date_iso: Optional[str] = None, to_date_iso: Optional[str] = None):
    res = compute_payroll_for_worker(worker_id, from_date_iso, to_date_iso)
    if "error" in res:
        raise HTTPException(status_code=400, detail=res["error"])
    return res

# ---------------------
# Estimation & Reports
# ---------------------
@router.get("/farmer/labour/estimate")
def api_estimate(stage: str, area_acres: float):
    return {"required_hours": estimate_labor_required(stage, area_acres)}

@router.get("/farmer/labour/shortage/{unit_id}")
def api_shortage(unit_id: str, stage: str, area_acres: float):
    return detect_labor_shortage(unit_id, stage, area_acres)

@router.get("/farmer/labour/efficiency/{unit_id}")
def api_efficiency(unit_id: str):
    return labor_efficiency_score(unit_id)

@router.get("/farmer/labour/summary/{unit_id}")
def api_summary(unit_id: str, stage: Optional[str] = None, area_acres: Optional[float] = 0.0):
    return labor_summary(unit_id, stage, area_acres or 0.0)

@router.get("/farmer/labour/available")
def api_find_available(skill_tags: Optional[str] = None, date_iso: Optional[str] = None):
    tags = skill_tags.split(",") if skill_tags else None
    return {"available_workers": find_available_workers(skill_tags=tags, date_iso=date_iso)}
