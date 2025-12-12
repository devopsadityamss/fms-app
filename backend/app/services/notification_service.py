# backend/app/services/notification_service.py

"""
Notifications & Alerts Engine (in-memory, stub-ready)
- send_notification: immediate send via configured channels (stubs)
- schedule_notification: schedule for later (in-memory store)
- list_history: list notifications, optionally filtered
- acknowledge / mark_read
- subscription preferences per user (channels + enabled types)
- templates store + simple formatting
- channel send stubs: push, email, sms (replace with real providers later)
"""

from datetime import datetime, timedelta
from threading import Lock
from typing import Dict, Any, List, Optional
import uuid
import time

_lock = Lock()

# Notification storage: notif_id -> notif record
_notification_store: Dict[str, Dict[str, Any]] = {}

# User subscription preferences: user_id -> { channels: ["push","sms","email"], types: ["booking","vision","alert", ...] }
_user_prefs: Dict[str, Dict[str, Any]] = {}

# Scheduled notifications (simple list); real system should use persistent scheduler / job queue
_scheduled_notifications: List[Dict[str, Any]] = []

# Templates: template_key -> {title_template, body_template}
_templates: Dict[str, Dict[str, str]] = {
    "booking_approved": {
        "title": "Your booking {{booking_id}} has been approved",
        "body": "Hello {{name}}, your booking {{booking_id}} for equipment {{equipment_title}} from {{start}} to {{end}} has been approved by {{provider_name}}."
    },
    "vision_alert": {
        "title": "Vision analysis: {{unit_name}} — {{status}}",
        "body": "Image analysis shows {{status}} with confidence {{confidence}} for unit {{unit_name}}. Recommendation: {{recommendation}}"
    },
    "generic": {
        "title": "{{title}}",
        "body": "{{body}}"
    }
}

# channel send stubs (replace with real integrations)
def _send_push(user_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    # stub: in production call FCM / APNs / push gateway
    return {"status": "sent", "channel": "push", "user_id": user_id, "payload": payload}

def _send_sms(phone: str, message: str) -> Dict[str, Any]:
    # stub: integrate with SMS gateway (Twilio, AWS SNS, etc.)
    return {"status": "sent", "channel": "sms", "to": phone, "message_preview": message[:120]}

def _send_email(email: str, subject: str, body: str) -> Dict[str, Any]:
    # stub: integrate with email provider (SES, Sendgrid, etc.)
    return {"status": "sent", "channel": "email", "to": email, "subject": subject}

# Public API

def _now_iso() -> str:
    return datetime.utcnow().isoformat()

def get_user_prefs(user_id: str) -> Dict[str, Any]:
    with _lock:
        return _user_prefs.get(user_id, {"channels": ["push"], "types": []})

def set_user_prefs(user_id: str, channels: Optional[List[str]]=None, types: Optional[List[str]]=None) -> Dict[str, Any]:
    with _lock:
        rec = _user_prefs.get(user_id, {"channels": ["push"], "types": []})
        if channels is not None:
            rec["channels"] = channels
        if types is not None:
            rec["types"] = types
        rec["updated_at"] = _now_iso()
        _user_prefs[user_id] = rec
    return rec

def render_template(template_key: str, vars: Dict[str, Any]) -> Dict[str, str]:
    tpl = _templates.get(template_key) or _templates["generic"]
    title = tpl.get("title","").replace("{{title}}", vars.get("title",""))
    body = tpl.get("body","").replace("{{body}}", vars.get("body",""))
    # simple replacement of {{var}} tokens
    for k,v in vars.items():
        token = "{{" + str(k) + "}}"
        title = title.replace(token, str(v))
        body = body.replace(token, str(v))
    return {"title": title, "body": body}

def send_notification(
    user_id: Optional[str],
    channels: Optional[List[str]],
    template_key: Optional[str],
    vars: Dict[str, Any],
    severity: str = "info",
    reference: Optional[Dict[str, Any]] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    user_id: target user (if None, must include metadata target). If multiple recipients needed, call multiple times or extend.
    channels: explicit channels to use; if None use user's prefs
    template_key: template to render; None => use generic title/body from vars
    vars: variables for template rendering
    severity: info|warning|critical
    reference: e.g., {"type":"booking","id":"booking_..."}
    metadata: any extra fields
    """
    notif_id = f"notif_{uuid.uuid4()}"
    # determine channels
    prefs = get_user_prefs(user_id) if user_id else {"channels": ["push"]}
    use_channels = channels or prefs.get("channels", ["push"])
    # render
    content = render_template(template_key or "generic", vars or {})
    rec = {
        "notif_id": notif_id,
        "user_id": user_id,
        "channels": use_channels,
        "template_key": template_key,
        "title": content.get("title"),
        "body": content.get("body"),
        "severity": severity,
        "reference": reference or {},
        "metadata": metadata or {},
        "created_at": _now_iso(),
        "delivered": [],
        "acknowledged": False,
        "acknowledged_at": None
    }

    # store
    with _lock:
        _notification_store[notif_id] = rec

    # send via channels (stubs)
    deliveries = []
    for ch in use_channels:
        try:
            if ch == "push":
                deliveries.append(_send_push(user_id, {"title": rec["title"], "body": rec["body"], "ref": rec["reference"]}))
            elif ch == "sms":
                # need phone in metadata or prefs
                phone = (prefs.get("phone") or metadata or {}).get("phone")
                if phone:
                    deliveries.append(_send_sms(phone, rec["body"]))
                else:
                    deliveries.append({"status":"skipped","reason":"no_phone"})
            elif ch == "email":
                email = (prefs.get("email") or metadata or {}).get("email")
                if email:
                    deliveries.append(_send_email(email, rec["title"], rec["body"]))
                else:
                    deliveries.append({"status":"skipped","reason":"no_email"})
            else:
                deliveries.append({"status":"skipped","reason":"unknown_channel"})
        except Exception as e:
            deliveries.append({"status":"error","channel":ch,"error":str(e)})

    # record delivery metadata
    with _lock:
        rec["delivered"] = deliveries
        _notification_store[notif_id] = rec

    return {"status": "queued_and_sent", "notification": rec, "deliveries": deliveries}

def list_history(limit:int=100, user_id:Optional[str]=None, unread_only:Optional[bool]=False) -> Dict[str,Any]:
    with _lock:
        items = list(_notification_store.values())
    # filter by user
    if user_id:
        items = [n for n in items if n.get("user_id")==user_id]
    if unread_only:
        items = [n for n in items if not n.get("acknowledged", False)]
    items_sorted = sorted(items, key=lambda x: x.get("created_at"), reverse=True)
    return {"count": len(items_sorted[:limit]), "history": items_sorted[:limit]}

def acknowledge_notification(notif_id: str, user_id: Optional[str]=None) -> Dict[str, Any]:
    with _lock:
        n = _notification_store.get(notif_id)
        if not n:
            return {"error":"not_found"}
        if user_id and n.get("user_id") and n.get("user_id")!=user_id:
            return {"error":"not_authorized"}
        n["acknowledged"]=True
        n["acknowledged_at"]=_now_iso()
        _notification_store[notif_id]=n
    return {"status":"acknowledged","notification":n}

def schedule_notification(
    send_at_iso: str,
    user_id: Optional[str],
    channels: Optional[List[str]],
    template_key: Optional[str],
    vars: Dict[str,Any],
    severity: str = "info",
    reference: Optional[Dict[str,Any]] = None,
    metadata: Optional[Dict[str,Any]] = None
) -> Dict[str,Any]:
    """
    Schedule a notification; stored in-memory and must be triggered by run_scheduled_notifications (manual or cron job)
    """
    sched_id = f"sched_{uuid.uuid4()}"
    rec = {
        "sched_id": sched_id,
        "send_at_iso": send_at_iso,
        "user_id": user_id,
        "channels": channels,
        "template_key": template_key,
        "vars": vars,
        "severity": severity,
        "reference": reference or {},
        "metadata": metadata or {},
        "created_at": _now_iso(),
        "status": "scheduled"
    }
    with _lock:
        _scheduled_notifications.append(rec)
    return rec

def run_scheduled_notifications(now_iso:Optional[str]=None) -> Dict[str,Any]:
    """
    Run due scheduled notifs. Intended to be called by an external scheduler (cron, worker).
    Returns list of sent notification ids.
    """
    now = now_iso or _now_iso()
    sent = []
    to_keep = []
    with _lock:
        for s in _scheduled_notifications:
            try:
                if s.get("status")!="scheduled":
                    to_keep.append(s); continue
                if s.get("send_at_iso") <= now:
                    # send
                    res = send_notification(
                        user_id=s.get("user_id"),
                        channels=s.get("channels"),
                        template_key=s.get("template_key"),
                        vars=s.get("vars"),
                        severity=s.get("severity"),
                        reference=s.get("reference"),
                        metadata=s.get("metadata")
                    )
                    s["status"]="sent"
                    s["sent_at"]=_now_iso()
                    sent.append(res.get("notification",{}).get("notif_id"))
                else:
                    to_keep.append(s)
            except Exception:
                # keep for retry
                to_keep.append(s)
        # replace schedule list
        _scheduled_notifications[:] = to_keep
    return {"sent_count": len(sent), "sent_ids": sent}

def list_scheduled(limit:int=200) -> Dict[str,Any]:
    with _lock:
        items = list(_scheduled_notifications)
    return {"count": len(items[:limit]), "scheduled": items[:limit]}

# Webhook integration: allow external listeners to receive copies (stub)
_webhook_listeners: List[Dict[str,Any]] = []

def register_webhook(url: str, secret: Optional[str]=None) -> Dict[str,Any]:
    rec = {"id": f"wh_{uuid.uuid4()}", "url": url, "secret": secret, "created_at": _now_iso()}
    with _lock:
        _webhook_listeners.append(rec)
    return rec

def list_webhooks() -> List[Dict[str,Any]]:
    with _lock:
        return list(_webhook_listeners)
