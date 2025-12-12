# backend/app/api/notification.py

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict, Any

from app.services.notification_service import (
    send_notification,
    list_history,
    acknowledge_notification,
    set_user_prefs,
    get_user_prefs,
    schedule_notification,
    list_scheduled,
    run_scheduled_notifications,
    register_webhook,
    list_webhooks,
    render_template
)

router = APIRouter()

# ---- Payloads ----
class SendPayload(BaseModel):
    user_id: Optional[str] = None
    channels: Optional[List[str]] = None
    template_key: Optional[str] = None
    vars: Dict[str, Any] = {}
    severity: Optional[str] = "info"
    reference: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None

class SchedulePayload(BaseModel):
    send_at_iso: str
    user_id: Optional[str] = None
    channels: Optional[List[str]] = None
    template_key: Optional[str] = None
    vars: Dict[str, Any] = {}
    severity: Optional[str] = "info"
    reference: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None

class PrefsPayload(BaseModel):
    user_id: str
    channels: Optional[List[str]] = None
    types: Optional[List[str]] = None

class RenderPayload(BaseModel):
    template_key: str
    vars: Dict[str, Any] = {}

class WebhookPayload(BaseModel):
    url: str
    secret: Optional[str] = None

# ---- Endpoints ----
@router.post("/notifications/send")
def api_send(req: SendPayload):
    res = send_notification(
        user_id=req.user_id,
        channels=req.channels,
        template_key=req.template_key,
        vars=req.vars or {},
        severity=req.severity or "info",
        reference=req.reference,
        metadata=req.metadata
    )
    return res

@router.get("/notifications/history")
def api_history(user_id: Optional[str] = None, limit: Optional[int] = 100, unread_only: Optional[bool] = False):
    return list_history(limit=limit or 100, user_id=user_id, unread_only=bool(unread_only))

@router.post("/notifications/{notif_id}/ack")
def api_ack(notif_id: str, user_id: Optional[str] = None):
    res = acknowledge_notification(notif_id, user_id=user_id)
    if "error" in res:
        raise HTTPException(status_code=404, detail=res["error"])
    return res

@router.post("/notifications/prefs")
def api_set_prefs(req: PrefsPayload):
    res = set_user_prefs(req.user_id, channels=req.channels, types=req.types)
    return res

@router.get("/notifications/prefs/{user_id}")
def api_get_prefs(user_id: str):
    return get_user_prefs(user_id)

@router.post("/notifications/schedule")
def api_schedule(req: SchedulePayload):
    res = schedule_notification(
        send_at_iso=req.send_at_iso,
        user_id=req.user_id,
        channels=req.channels,
        template_key=req.template_key,
        vars=req.vars or {},
        severity=req.severity or "info",
        reference=req.reference,
        metadata=req.metadata
    )
    return res

@router.get("/notifications/scheduled")
def api_get_scheduled(limit: Optional[int] = 200):
    return list_scheduled(limit=limit or 200)

@router.post("/notifications/scheduled/run")
def api_run_scheduled(now_iso: Optional[str] = None):
    # manual trigger for testing: returns sent ids
    return run_scheduled_notifications(now_iso=now_iso)

@router.post("/notifications/template/render")
def api_render_template(req: RenderPayload):
    return render_template(req.template_key, req.vars or {})

@router.post("/notifications/webhook/register")
def api_register_webhook(req: WebhookPayload):
    return register_webhook(req.url, secret=req.secret)

@router.get("/notifications/webhooks")
def api_list_webhooks():
    return {"webhooks": list_webhooks()}
