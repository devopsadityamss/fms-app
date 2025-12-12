"""
Photo Timeline Service (stub-ready)
-----------------------------------

Responsibilities:
 - Accept image bytes + metadata and store in-memory
 - Optionally call vision_service.analyze_image if present to attach analysis
 - Provide CRUD and list/filtering for timeline UI
 - Provide timeline feed entries sorted by captured_at

Stored record shape:
{
  "id": "<uuid>",
  "unit_id": "unit-12",
  "filename": "leaf.jpg",
  "content_type": "image/jpeg",
  "bytes": b"...",                # in-memory binary (can be large; replace with storage later)
  "tags": ["leaf","pest"],
  "notes": "taken near gate",
  "captured_at": "2025-12-12T06:00:00Z",
  "uploaded_at": "2025-12-12T06:01:00Z",
  "vision_analysis": { ... } or None
}
"""

from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime
import uuid
import imghdr

# in-memory store: photo_id -> record
_photo_store: Dict[str, Dict[str, Any]] = {}

# optional vision integration
try:
    from app.services.farmer import vision_service as vision_svc
except Exception:
    vision_svc = None


def _new_id() -> str:
    return str(uuid.uuid4())


def _now_iso() -> str:
    return datetime.utcnow().isoformat()


def _detect_content_type_from_bytes(b: bytes, filename: Optional[str] = None) -> str:
    """
    Try to detect image type. Fallback to 'application/octet-stream'.
    """
    try:
        t = imghdr.what(None, h=b)
        if t:
            return f"image/{t if t != 'jpeg' else 'jpeg'}"
    except Exception:
        pass
    # fallback by filename extension
    if filename:
        fn = filename.lower()
        if fn.endswith(".png"):
            return "image/png"
        if fn.endswith(".jpg") or fn.endswith(".jpeg"):
            return "image/jpeg"
        if fn.endswith(".webp"):
            return "image/webp"
    return "application/octet-stream"


def add_photo(
    img_bytes: bytes,
    filename: Optional[str] = None,
    unit_id: Optional[str] = None,
    tags: Optional[List[str]] = None,
    notes: Optional[str] = None,
    captured_at: Optional[str] = None,
    run_vision_analysis: bool = True
) -> Dict[str, Any]:
    """
    Store image bytes and metadata in-memory. Optionally call vision_service.analyze_image
    to attach an analysis snapshot.
    """
    pid = _new_id()
    ct = _detect_content_type_from_bytes(img_bytes, filename)

    captured_at_val = captured_at or _now_iso()

    record = {
        "id": pid,
        "unit_id": unit_id,
        "filename": filename,
        "content_type": ct,
        "bytes": img_bytes,   # keep in-memory; replace with object storage later
        "tags": tags or [],
        "notes": notes,
        "captured_at": captured_at_val,
        "uploaded_at": _now_iso(),
        "vision_analysis": None,
    }

    # optionally call vision analysis (non-fatal)
    if run_vision_analysis and vision_svc:
        try:
            # some vision services expect bytes and return a dict
            analysis = vision_svc.analyze_image(img_bytes, unit_id=unit_id, tags=tags)
            record["vision_analysis"] = analysis
        except Exception:
            record["vision_analysis"] = None

    _photo_store[pid] = record
    return record


def get_photo(photo_id: str) -> Dict[str, Any]:
    rec = _photo_store.get(photo_id)
    if not rec:
        return {"error": "not_found"}
    # return shallow copy without raw bytes to keep metadata responses light
    return {
        k: v for k, v in rec.items() if k != "bytes"
    }


def get_photo_bytes(photo_id: str) -> Optional[Tuple[bytes, str, Optional[str]]]:
    """
    Returns (bytes, content_type, filename) or None if not found.
    """
    rec = _photo_store.get(photo_id)
    if not rec:
        return None
    return (rec.get("bytes"), rec.get("content_type"), rec.get("filename"))


def delete_photo(photo_id: str) -> bool:
    if photo_id in _photo_store:
        del _photo_store[photo_id]
        return True
    return False


def list_photos(
    unit_id: Optional[str] = None,
    tag: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    limit: int = 100,
    offset: int = 0
) -> Dict[str, Any]:
    """
    Filter photos by unit, tag, and date range (captured_at).
    Returns metadata only (no raw bytes).
    """
    items = list(_photo_store.values())

    if unit_id:
        items = [i for i in items if i.get("unit_id") == unit_id]

    if tag:
        items = [i for i in items if tag in (i.get("tags") or [])]

    # parse date range (ISO strings). If invalid, ignore filter silently
    try:
        df = datetime.fromisoformat(date_from) if date_from else None
    except Exception:
        df = None
    try:
        dt = datetime.fromisoformat(date_to) if date_to else None
    except Exception:
        dt = None

    if df or dt:
        filtered = []
        for i in items:
            try:
                cap = datetime.fromisoformat(i.get("captured_at"))
            except Exception:
                continue
            if df and cap < df:
                continue
            if dt and cap > dt:
                continue
            filtered.append(i)
        items = filtered

    # sort by captured_at desc
    items_sorted = sorted(items, key=lambda x: x.get("captured_at", ""), reverse=True)

    # paginate
    slice_items = items_sorted[offset: offset + limit]

    # return metadata without bytes
    out = []
    for r in slice_items:
        d = {k: v for k, v in r.items() if k != "bytes"}
        out.append(d)

    return {"count": len(items_sorted), "items": out}


def timeline_feed(
    unit_id: Optional[str] = None,
    days_back: Optional[int] = None,
    limit: int = 100
) -> Dict[str, Any]:
    """
    Returns a timeline-style feed with recent photo events.
    days_back: if provided, include only photos captured within N days from now.
    """
    items = list(_photo_store.values())

    if unit_id:
        items = [i for i in items if i.get("unit_id") == unit_id]

    if days_back:
        cutoff = datetime.utcnow() - timedelta(days=int(days_back))
        items = [i for i in items if _parse_iso(i.get("captured_at")) and datetime.fromisoformat(i.get("captured_at")) >= cutoff]

    items_sorted = sorted(items, key=lambda x: x.get("captured_at", ""), reverse=True)
    slice_items = items_sorted[:limit]

    feed = []
    for r in slice_items:
        feed.append({
            "id": r["id"],
            "unit_id": r.get("unit_id"),
            "title": r.get("notes") or (r.get("filename") or "Photo"),
            "captured_at": r.get("captured_at"),
            "tags": r.get("tags"),
            "vision_summary": _summarize_vision(r.get("vision_analysis"))
        })
    return {"count": len(feed), "items": feed}


# small helpers
def _parse_iso(s: Optional[str]):
    if not s:
        return None
    try:
        return datetime.fromisoformat(s)
    except Exception:
        return None


def _summarize_vision(analysis: Optional[Dict[str, Any]]) -> Optional[str]:
    if not analysis:
        return None
    # lightweight summary: health + pest if present
    parts = []
    h = analysis.get("health_assessment") or analysis.get("health")
    if h:
        if isinstance(h, dict):
            parts.append(f"Health {h.get('status')} conf {h.get('confidence')}")
        else:
            parts.append(str(h))
    p = analysis.get("pest_assessment") or analysis.get("pest")
    if p:
        if isinstance(p, dict):
            parts.append(f"Pest risk {p.get('risk_score') or p.get('risk')}")
        else:
            parts.append(str(p))
    return " | ".join(parts) if parts else None


def _clear_store():
    _photo_store.clear()
