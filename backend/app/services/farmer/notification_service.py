# backend/app/services/farmer/notification_service.py

"""
backend/app/services/farmer/notification_service.py
In-memory, farmer-focused notification engine.
Key concepts:
 - subscriptions: farmer-level preferences (channels: in_app, email, sms)
 - triggers (scheduled notifications): stores rules and times
 - notification history (delivered/stubbed)
 - run_due_notifications() must be called periodically by your scheduler (cron/k8s job) or invoked from code
 - immediate_send() for ad-hoc alerts
 - send stubs: send_in_app (stores), send_email_stub, send_sms_stub (log-only)
"""
from datetime import datetime
from typing import List, Dict, Any


# NOTE:
# This service creates mock notifications for:
# - weather alerts
# - pest/disease alerts
# - overdue tasks
# - stage reminders
# - health score warnings
# - recommended actions
#
# Later this will integrate with:
# - SMS APIs (Twilio, MSG91)
# - Push notifications
# - WhatsApp messaging
# - Firebase Cloud Messaging
#
# For now: lightweight logic for UI & API integration.


def create_notification(message: str, category: str, severity: str = "info") -> Dict[str, Any]:
    """
    Creates a standard notification object.
    """

    return {
        "message": message,
        "category": category,
        "severity": severity,
        "timestamp": datetime.utcnow(),
        "read": False,
    }


# -------------------------------------------------------------------
# WEATHER NOTIFICATIONS
# -------------------------------------------------------------------

def get_weather_notifications(weather: Dict[str, Any]) -> List[Dict[str, Any]]:
    notifications = []

    temp = weather.get("temperature", 0)
    rainfall = weather.get("rainfall_mm", 0)

    if temp > 35:
        notifications.append(
            create_notification(
                "High temperature detected — irrigate in early morning or evening.",
                category="weather",
                severity="high"
            )
        )

    if rainfall > 15:
        notifications.append(
            create_notification(
                "Heavy rainfall expected — postpone fertilizer application.",
                category="weather",
                severity="medium"
            )
        )

    return notifications


# -------------------------------------------------------------------
# TASK NOTIFICATIONS
# -------------------------------------------------------------------

def get_task_notifications(overdue_tasks: int, upcoming_tasks: int = 0) -> List[Dict[str, Any]]:
    notifications = []

    if overdue_tasks > 0:
        notifications.append(
            create_notification(
                f"You have {overdue_tasks} overdue tasks.",
                category="task",
                severity="high"
            )
        )

    if upcoming_tasks > 0:
        notifications.append(
            create_notification(
                f"{upcoming_tasks} tasks scheduled for today.",
                category="task",
                severity="info"
            )
        )

    return notifications


# -------------------------------------------------------------------
# HEALTH SCORE NOTIFICATIONS
# -------------------------------------------------------------------

def get_health_notifications(health_score: int) -> List[Dict[str, Any]]:
    notifications = []

    if health_score < 50:
        notifications.append(
            create_notification(
                "Crop health is declining. Check irrigation, nutrients, and pest conditions.",
                category="health",
                severity="high"
            )
        )
    elif health_score < 70:
        notifications.append(
            create_notification(
                "Crop health is moderate. Review advisory suggestions.",
                category="health",
                severity="medium"
            )
        )

    return notifications


# -------------------------------------------------------------------
# PEST/DISEASE NOTIFICATIONS
# -------------------------------------------------------------------

def get_pest_notifications(pest_alerts_count: int) -> List[Dict[str, Any]]:
    notifications = []

    if pest_alerts_count > 0:
        notifications.append(
            create_notification(
                f"{pest_alerts_count} pest/disease alerts detected. Inspect field immediately.",
                category="pest",
                severity="high"
            )
        )

    return notifications


# -------------------------------------------------------------------
# STAGE TRANSITION NOTIFICATIONS
# -------------------------------------------------------------------

def get_stage_transition_notification(stage_name: str) -> List[Dict[str, Any]]:
    """
    Alerts farmer when a crop stage changes.
    """

    return [
        create_notification(
            f"Crop has entered the '{stage_name}' stage. Follow recommended activities.",
            category="stage",
            severity="info"
        )
    ]


# -------------------------------------------------------------------
# UNIFIED NOTIFICATION ENGINE
# -------------------------------------------------------------------

def get_all_notifications(
    unit_id: int,
    weather: Dict[str, Any],
    health_score: int,
    overdue_tasks: int,
    upcoming_tasks: int,
    pest_alerts_count: int,
    stage_name: str
) -> Dict[str, Any]:
    """
    Collects ALL relevant notifications for a farmer.
    """

    notifications = []

    notifications += get_weather_notifications(weather)
    notifications += get_task_notifications(overdue_tasks, upcoming_tasks)
    notifications += get_health_notifications(health_score)
    notifications += get_pest_notifications(pest_alerts_count)
    notifications += get_stage_transition_notification(stage_name)

    return {
        "unit_id": unit_id,
        "timestamp": datetime.utcnow(),
        "notifications": notifications
    }

from datetime import datetime, timedelta
from threading import Lock
from typing import Dict, Any, List, Optional
import uuid
# stores
_subscriptions: Dict[str, Dict[str, Any]] = {} # farmer_id -> { channels: [...], email, phone, created_at }
_triggers: Dict[str, Dict[str, Any]] = {} # trigger_id -> { farmer_id, title, body, channels, next_run_iso, cron_like (optional), metadata, active }
_history: Dict[str, Dict[str, Any]] = {} # notif_id -> delivered record
_lock = Lock()
# channel constants
CHANNEL_IN_APP = "in_app"
CHANNEL_EMAIL = "email"
CHANNEL_SMS = "sms"
# -----------------------
# Subscription API
# -----------------------
def subscribe_farmer(farmer_id: str, channels: Optional[List[str]] = None, email: Optional[str] = None, phone: Optional[str] = None) -> Dict[str, Any]:
    rec = {
        "farmer_id": farmer_id,
        "channels": channels or [CHANNEL_IN_APP],
        "email": email,
        "phone": phone,
        "created_at": datetime.utcnow().isoformat()
    }
    with _lock:
        _subscriptions[farmer_id] = rec
    return rec
def get_subscription(farmer_id: str) -> Dict[str, Any]:
    with _lock:
        return _subscriptions.get(farmer_id, {})
def list_subscriptions() -> Dict[str, Any]:
    with _lock:
        return {"count": len(_subscriptions), "subscriptions": list(_subscriptions.values())}
# -----------------------
# Trigger scheduling
# -----------------------
def create_scheduled_trigger(
    farmer_id: str,
    title: str,
    body: str,
    run_at_iso: Optional[str] = None,
    channels: Optional[List[str]] = None,
    repeat_every_minutes: Optional[int] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    - run_at_iso: ISO timestamp for first run (if omitted, runs immediately when run_due is called)
    - repeat_every_minutes: if provided, after delivery next_run will be bumped by this many minutes (simple interval)
    """
    tid = str(uuid.uuid4())
    rec = {
        "trigger_id": tid,
        "farmer_id": farmer_id,
        "title": title,
        "body": body,
        "channels": channels or None, # None => use subscription channels
        "next_run_iso": run_at_iso,
        "repeat_every_minutes": int(repeat_every_minutes) if repeat_every_minutes else None,
        "metadata": metadata or {},
        "active": True,
        "created_at": datetime.utcnow().isoformat()
    }
    with _lock:
        _triggers[tid] = rec
    return rec
def list_triggers(farmer_id: Optional[str] = None, active_only: bool = True) -> Dict[str, Any]:
    with _lock:
        items = list(_triggers.values())
    if farmer_id:
        items = [t for t in items if t.get("farmer_id") == farmer_id]
    if active_only:
        items = [t for t in items if t.get("active")]
    return {"count": len(items), "triggers": items}
def deactivate_trigger(trigger_id: str) -> Dict[str, Any]:
    with _lock:
        t = _triggers.get(trigger_id)
        if not t:
            return {"error": "trigger_not_found"}
        t["active"] = False
        t["deactivated_at"] = datetime.utcnow().isoformat()
        _triggers[trigger_id] = t
    return t
# -----------------------
# Notification delivery (stubs + in-app storage)
# -----------------------
def _deliver_in_app(farmer_id: str, title: str, body: str, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    nid = str(uuid.uuid4())
    rec = {
        "notif_id": nid,
        "farmer_id": farmer_id,
        "channel": CHANNEL_IN_APP,
        "title": title,
        "body": body,
        "metadata": metadata or {},
        "delivered_at": datetime.utcnow().isoformat(),
        "status": "delivered"
    }
    with _lock:
        _history[nid] = rec
    return rec
def _send_email_stub(email: str, title: str, body: str, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Placeholder — integrate with actual email provider. For now we store a record with channel=email and status=stubbed.
    """
    nid = str(uuid.uuid4())
    rec = {
        "notif_id": nid,
        "farmer_id": None,
        "channel": CHANNEL_EMAIL,
        "to": email,
        "title": title,
        "body": body,
        "metadata": metadata or {},
        "delivered_at": datetime.utcnow().isoformat(),
        "status": "stubbed_email"
    }
    with _lock:
        _history[nid] = rec
    return rec
def _send_sms_stub(phone: str, body: str, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    nid = str(uuid.uuid4())
    rec = {
        "notif_id": nid,
        "farmer_id": None,
        "channel": CHANNEL_SMS,
        "to": phone,
        "title": None,
        "body": body,
        "metadata": metadata or {},
        "delivered_at": datetime.utcnow().isoformat(),
        "status": "stubbed_sms"
    }
    with _lock:
        _history[nid] = rec
    return rec
def immediate_send(
    farmer_id: str,
    title: str,
    body: str,
    channels: Optional[List[str]] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Immediately deliver via requested channels (or via farmer subscription channels if channels is None).
    Returns list of delivery records.
    """
    subs = get_subscription(farmer_id) or {}
    use_channels = channels or subs.get("channels") or [CHANNEL_IN_APP]
    deliveries = []
    for ch in use_channels:
        if ch == CHANNEL_IN_APP:
            deliveries.append(_deliver_in_app(farmer_id, title, body, metadata=metadata))
        elif ch == CHANNEL_EMAIL:
            email = subs.get("email")
            if email:
                deliveries.append(_send_email_stub(email, title, body, metadata=metadata))
            else:
                deliveries.append({"error": "no_email_on_subscription", "channel": ch})
        elif ch == CHANNEL_SMS:
            phone = subs.get("phone")
            if phone:
                deliveries.append(_send_sms_stub(phone, body, metadata=metadata))
            else:
                deliveries.append({"error": "no_phone_on_subscription", "channel": ch})
        else:
            deliveries.append({"error": "unknown_channel", "channel": ch})
    return {"deliveries": deliveries, "count": len(deliveries)}
# -----------------------
# Run due triggers (to be invoked by scheduler)
# -----------------------
def run_due_notifications(now_iso: Optional[str] = None, force_run_all: bool = False) -> Dict[str, Any]:
    """
    - If force_run_all is True: run all active triggers regardless of next_run_iso.
    - Otherwise: run triggers with next_run_iso <= now (or next_run_iso is None -> treat as due).
    - After running: mark history entries and update trigger.next_run_iso if repeat_every_minutes is set.
    """
    now = datetime.fromisoformat(now_iso) if now_iso else datetime.utcnow()
    run_results = []
    to_update = []
    with _lock:
        triggers = list(_triggers.values())
    for t in triggers:
        if not t.get("active", True):
            continue
        due = False
        if force_run_all:
            due = True
        else:
            niso = t.get("next_run_iso")
            if not niso:
                due = True
            else:
                try:
                    nxt = datetime.fromisoformat(niso)
                    if nxt <= now:
                        due = True
                except Exception:
                    due = True
        if not due:
            continue
        farmer_id = t.get("farmer_id")
        channels = t.get("channels")
        # immediate send for this trigger
        delivered = immediate_send(farmer_id, t.get("title"), t.get("body"), channels=channels, metadata=t.get("metadata"))
        run_results.append({"trigger_id": t["trigger_id"], "delivered": delivered})
        # update next_run_iso if repeating
        rpt = t.get("repeat_every_minutes")
        if rpt:
            try:
                nxt_dt = (datetime.fromisoformat(t.get("next_run_iso")) if t.get("next_run_iso") else now) + timedelta(minutes=rpt)
            except Exception:
                nxt_dt = now + timedelta(minutes=rpt)
            t["next_run_iso"] = nxt_dt.isoformat()
            with _lock:
                _triggers[t["trigger_id"]] = t
        else:
            # one-off: deactivate it
            t["active"] = False
            with _lock:
                _triggers[t["trigger_id"]] = t
    return {"run_at": now.isoformat(), "results": run_results, "run_count": len(run_results)}
# -----------------------
# History & acknowledgment
# -----------------------
def list_history(limit: int = 50) -> Dict[str, Any]:
    with _lock:
        items = sorted(list(_history.values()), key=lambda x: x.get("delivered_at", ""), reverse=True)
    return {"count": len(items[:limit]), "history": items[:limit]}
def ack_notification(notif_id: str, acknowledged_by: Optional[str] = None) -> Dict[str, Any]:
    with _lock:
        rec = _history.get(notif_id)
        if not rec:
            return {"error": "notif_not_found"}
        rec["acknowledged"] = True
        rec["acknowledged_by"] = acknowledged_by
        rec["acknowledged_at"] = datetime.utcnow().isoformat()
        _history[notif_id] = rec
    return rec