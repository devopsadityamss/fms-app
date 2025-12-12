# backend/app/api/farmer/notification.py

"""
backend/app/api/farmer/notification.py
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from app.services.farmer.notification_service import (
    subscribe_farmer,
    get_subscription,
    list_subscriptions,
    create_scheduled_trigger,
    list_triggers,
    deactivate_trigger,
    immediate_send,
    run_due_notifications,
    list_history,
    ack_notification
)
from app.services.farmer.notification_service import (
    get_weather_notifications,
    get_task_notifications,
    get_health_notifications,
    get_pest_notifications,
    get_stage_transition_notification,
    get_all_notifications,
)   # ← ADDED
from app.services.farmer.weather_service import get_current_weather   # ← ADDED
from app.services.farmer.health_service import get_crop_health_score   # ← ADDED
from app.services.farmer.alert_service import get_disease_and_pest_alerts   # ← ADDED

router = APIRouter()
# -------- payloads
class SubscriptionPayload(BaseModel):
    farmer_id: str
    channels: Optional[List[str]] = None
    email: Optional[str] = None
    phone: Optional[str] = None
class TriggerPayload(BaseModel):
    farmer_id: str
    title: str
    body: str
    run_at_iso: Optional[str] = None
    channels: Optional[List[str]] = None
    repeat_every_minutes: Optional[int] = None
    metadata: Optional[Dict[str, Any]] = None
class ImmediatePayload(BaseModel):
    farmer_id: str
    title: str
    body: str
    channels: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None
class RunPayload(BaseModel):
    now_iso: Optional[str] = None
    force_run_all: Optional[bool] = False
# -------- endpoints
@router.post("/notify/subscribe")
def api_subscribe(req: SubscriptionPayload):
    res = subscribe_farmer(req.farmer_id, channels=req.channels, email=req.email, phone=req.phone)
    return res
@router.get("/notify/subscription/{farmer_id}")
def api_get_subscription(farmer_id: str):
    res = get_subscription(farmer_id)
    if not res:
        raise HTTPException(status_code=404, detail="subscription_not_found")
    return res
@router.get("/notify/subscriptions")
def api_list_subscriptions():
    return list_subscriptions()
@router.post("/notify/trigger/create")
def api_create_trigger(req: TriggerPayload):
    return create_scheduled_trigger(
        req.farmer_id, req.title, req.body, run_at_iso=req.run_at_iso,
        channels=req.channels, repeat_every_minutes=req.repeat_every_minutes, metadata=req.metadata
    )
@router.get("/notify/triggers")
def api_list_triggers(farmer_id: Optional[str] = None, active_only: Optional[bool] = True):
    return list_triggers(farmer_id=farmer_id, active_only=active_only)
@router.post("/notify/trigger/{trigger_id}/deactivate")
def api_deactivate_trigger(trigger_id: str):
    res = deactivate_trigger(trigger_id)
    if "error" in res:
        raise HTTPException(status_code=404, detail=res["error"])
    return res
@router.post("/notify/send")
def api_immediate_send(req: ImmediatePayload):
    return immediate_send(req.farmer_id, req.title, req.body, channels=req.channels, metadata=req.metadata)
@router.post("/notify/run")
def api_run_due(req: RunPayload):
    res = run_due_notifications(now_iso=req.now_iso, force_run_all=bool(req.force_run_all))
    return res
@router.get("/notify/history")
def api_history(limit: int = 50):
    return list_history(limit=limit)
@router.post("/notify/ack/{notif_id}")
def api_ack(notif_id: str, acknowledged_by: Optional[str] = None):
    res = ack_notification(notif_id, acknowledged_by=acknowledged_by)
    if "error" in res:
        raise HTTPException(status_code=404, detail=res["error"])
    return res


# ------------------------------
# NEW MOCK NOTIFICATION ENDPOINTS
# ------------------------------

@router.get("/notifications/{unit_id}")
def notifications_overview(
    unit_id: int,
    stage: str,
    overdue_tasks: int = 0,
    upcoming_tasks: int = 0
):
    """
    Returns unified notification feed for:
    - weather alerts
    - task reminders
    - health warnings
    - pest/disease notifications
    - stage transition alerts
    """

    # Weather data
    weather = get_current_weather(unit_id)

    # Health score (used for threshold warnings)
    health_score = get_crop_health_score(unit_id, stage, weather)["score"]

    # Pest alerts (count only)
    pest_alerts_count = len(get_disease_and_pest_alerts(unit_id, stage))

    return get_all_notifications(
        unit_id=unit_id,
        weather=weather,
        health_score=health_score,
        overdue_tasks=overdue_tasks,
        upcoming_tasks=upcoming_tasks,
        pest_alerts_count=pest_alerts_count,
        stage_name=stage,
    )


@router.get("/notifications/{unit_id}/weather")
def notifications_weather(unit_id: int):
    weather = get_current_weather(unit_id)
    return get_weather_notifications(weather)


@router.get("/notifications/{unit_id}/tasks")
def notifications_tasks(unit_id: int, overdue_tasks: int = 0, upcoming_tasks: int = 0):
    return get_task_notifications(overdue_tasks, upcoming_tasks)


@router.get("/notifications/{unit_id}/health")
def notifications_health(unit_id: int, stage: str):
    weather = get_current_weather(unit_id)
    health_score = get_crop_health_score(unit_id, stage, weather)["score"]
    return get_health_notifications(health_score)


@router.get("/notifications/{unit_id}/pest")
def notifications_pest(unit_id: int, stage: str):
    pest_alerts = len(get_disease_and_pest_alerts(unit_id, stage))
    return get_pest_notifications(pest_alerts)


@router.get("/notifications/{unit_id}/stage")
def notifications_stage(unit_id: int, stage: str):
    return get_stage_transition_notification(stage)