"""
Vision -> Timeline Integration Service (stub-ready)
--------------------------------------------------

Responsibilities:
 - Accept an image analysis record (or image_id)
 - Create a calendar/timeline event summarizing the analysis
 - Keep integration records in-memory
 - Optionally call activity_calendar_service.create_event if present
 - Designed so Vision service records (feature #265) can be linked without changing API
"""

from typing import Dict, Any, Optional
from datetime import datetime
import uuid

# in-memory store for integration records
_integration_store: Dict[str, Dict[str, Any]] = {}

# optional dependency: activity calendar service (to auto-create events)
try:
    from app.services.farmer import activity_calendar_service as calendar_svc
except Exception:
    calendar_svc = None

# optional dependency: vision store helper (if you want to fetch analysis by id)
try:
    from app.services.farmer import vision_service as vision_svc
except Exception:
    vision_svc = None


def _now() -> str:
    return datetime.utcnow().isoformat()


def _new_id() -> str:
    return str(uuid.uuid4())


def _summarize_analysis(analysis: Dict[str, Any]) -> str:
    """
    Build a short human-readable summary from an analysis record.
    This is intentionally conservative: pick a few notable fields if present.
    """
    parts = []
    if not analysis:
        return "Image analysis record unavailable."

    # health
    h = analysis.get("health_assessment") or analysis.get("health")
    if h:
        if isinstance(h, dict):
            parts.append(f"Health: {h.get('status','unknown')} (conf {h.get('confidence')})")
        else:
            parts.append(f"Health: {str(h)}")

    # pest
    p = analysis.get("pest_assessment") or analysis.get("pest")
    if p:
        if isinstance(p, dict):
            parts.append(f"Pest risk: {p.get('risk_score', p.get('risk', 'n/a'))}")
        else:
            parts.append(f"Pest: {str(p)}")

    # nutrient
    n = analysis.get("nutrient_assessment") or analysis.get("nutrient")
    if n:
        if isinstance(n, dict):
            parts.append(f"Nutrient hint: {n.get('suggestion')}")
        else:
            parts.append(f"Nutrient: {str(n)}")

    # moisture
    m = analysis.get("soil_moisture_assessment") or analysis.get("moisture")
    if m:
        if isinstance(m, dict):
            parts.append(f"Soil moisture: {m.get('moisture')}")
        else:
            parts.append(f"Soil moisture: {str(m)}")

    # fallback: dominant color or metadata
    dom = analysis.get("dominant_color_rgb") or analysis.get("dominant_color")
    if dom:
        parts.append(f"Dominant color: {dom}")

    if not parts:
        parts.append("No notable findings from image analysis.")

    return " | ".join(parts)


# -------------------------
# Main integration function
# -------------------------
def integrate_image_analysis(
    image_id: Optional[str] = None,
    analysis_record: Optional[Dict[str, Any]] = None,
    create_timeline_event: bool = True,
    event_category: str = "vision_analysis",
    event_title_prefix: str = "Image Analysis",
    notes: Optional[str] = None
) -> Dict[str, Any]:
    """
    Either pass `analysis_record` directly, or pass `image_id` (and ensure vision_service is importable).
    If create_timeline_event=True and activity_calendar_service exists, this will attempt to create an event.
    Returns the integration record that contains references to the analysis and any created event.
    """

    # fetch analysis if only image_id supplied
    analysis = analysis_record
    if image_id and analysis is None and vision_svc:
        try:
            analysis = vision_svc.get_image_analysis(image_id)
        except Exception:
            analysis = None

    integration_id = _new_id()
    summary = _summarize_analysis(analysis or {})

    record = {
        "id": integration_id,
        "image_id": image_id,
        "created_at": _now(),
        "analysis_snapshot": analysis,
        "summary": summary,
        "notes": notes,
        "event_created": None,
    }

    # attempt to create timeline event if requested and calendar service is available
    if create_timeline_event and calendar_svc:
        try:
            title = f"{event_title_prefix}: { (analysis.get('unit_id') or image_id) }"
            # event payload — keep minimal and consistent with calendar service
            payload = {
                "unit_id": (analysis.get("unit_id") if isinstance(analysis, dict) else None),
                "title": title,
                "event_type": "advisory" if (analysis and analysis.get("health_assessment")) else "misc",
                "start_time": _now(),
                "end_time": None,
                "notes": summary,
                "meta": {
                    "source": "vision_integration",
                    "image_id": image_id
                }
            }
            evt = calendar_svc.create_event(payload)
            record["event_created"] = evt
        except Exception:
            # non-fatal: keep integration record even if event creation fails
            record["event_created"] = {"error": "event_creation_failed"}

    _integration_store[integration_id] = record
    return record


# -------------------------
# Accessors
# -------------------------
def get_integration(integration_id: str) -> Optional[Dict[str, Any]]:
    return _integration_store.get(integration_id)


def list_integrations(unit_id: Optional[str] = None) -> Dict[str, Any]:
    items = list(_integration_store.values())
    if unit_id:
        items = [i for i in items if i.get("analysis_snapshot", {}).get("unit_id") == unit_id]
    return {"count": len(items), "items": items}


def _clear_store():
    _integration_store.clear()
