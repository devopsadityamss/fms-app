# backend/app/services/farmer/unified_search_service.py

from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
import re

# Best-effort imports of in-memory stores used across modules
try:
    from app.services.farmer.unit_service import _unit_store
except Exception:
    _unit_store = {}

try:
    from app.services.farmer.task_service import _task_templates_store
except Exception:
    _task_templates_store = {}

try:
    from app.services.farmer.risk_alerts_service import _alerts_store as _risk_alerts_store
except Exception:
    _risk_alerts_store = {}

try:
    from app.services.farmer.season_calendar_service import _calendar_store
except Exception:
    _calendar_store = {}

try:
    from app.services.farmer.input_shortage_service import _input_inventory_store
except Exception:
    _input_inventory_store = {}

try:
    from app.services.farmer.financial_ledger_service import _ledger_store
except Exception:
    _ledger_store = []

try:
    from app.services.farmer.peer_benchmark_service import _peer_store
except Exception:
    _peer_store = {}

# Also support recommendation engine live hits (best-effort)
try:
    from app.services.farmer.recommendation_engine_service import generate_recommendations_for_unit
except Exception:
    generate_recommendations_for_unit = None


# ---------- Utilities ----------
def _normalize_text(s: Optional[str]) -> str:
    if s is None:
        return ""
    return re.sub(r'\s+', ' ', str(s).strip().lower())


def _score_match(query: str, text: str) -> float:
    """
    Simple fuzzy scoring:
     - exact token match => higher
     - prefix match => good
     - substring match => mid
     - token overlap ratio adds points
    Scores range approx 0-100.
    """
    if not query or not text:
        return 0.0

    q = query.lower()
    t = text.lower()

    if q == t:
        return 100.0

    score = 0.0
    if q in t:
        # substring match base
        score += 40.0
        # longer matches get more
        score += min(40.0, (len(q) / max(1, len(t))) * 40.0)
    # token overlap
    q_tokens = set(q.split())
    t_tokens = set(t.split())
    common = q_tokens.intersection(t_tokens)
    if common:
        ratio = len(common) / max(1, len(q_tokens))
        score += min(20.0, ratio * 30.0)

    # prefix boost
    for tok in t.split():
        if tok.startswith(q):
            score += 10.0
            break

    return round(min(100.0, score), 2)


def _build_snippet(query: str, text: str, length: int = 120) -> str:
    text = text or ""
    idx = text.lower().find(query.lower())
    if idx == -1:
        # return start truncated
        return (text[:length] + "...") if len(text) > length else text
    start = max(0, idx - 30)
    snippet = text[start:start + length]
    if start > 0:
        snippet = "..." + snippet
    if len(text) > start + length:
        snippet = snippet + "..."
    return snippet


# ---------- Indexing helpers ----------
def _index_units() -> List[Dict[str, Any]]:
    items = []
    for uid, u in _unit_store.items():
        title = u.get("name") or f"unit_{uid}"
        text = " ".join(filter(None, [
            title,
            str(u.get("crop") or ""),
            str(u.get("notes") or ""),
            str(u.get("stage_template_id") or ""),
            str(u.get("location") or "")
        ]))
        items.append({"type": "unit", "id": uid, "title": title, "text": _normalize_text(text), "raw": u})
    return items


def _index_tasks() -> List[Dict[str, Any]]:
    items = []
    for tid, t in _task_templates_store.items():
        title = t.get("name") or f"task_{tid}"
        text = " ".join(filter(None, [title, str(t.get("description") or ""), str(t.get("type") or "")]))
        items.append({"type": "task_template", "id": tid, "title": title, "text": _normalize_text(text), "raw": t})
    return items


def _index_alerts() -> List[Dict[str, Any]]:
    items = []
    for aid, a in _risk_alerts_store.items():
        title = a.get("kind") or a.get("message") or aid
        text = " ".join(filter(None, [title, str(a.get("message") or ""), str(a.get("evidence") or "")]))
        items.append({"type": "alert", "id": aid, "title": title, "text": _normalize_text(text), "raw": a})
    return items


def _index_calendars() -> List[Dict[str, Any]]:
    items = []
    for uid, cal in _calendar_store.items():
        title = f"calendar_{uid}"
        # flatten entries as searchable text
        entries_txt = " ".join([f"{e.get('task_name')} {e.get('stage_name')} {e.get('scheduled_start_iso')}" for e in cal.get("entries", [])])
        items.append({"type": "calendar", "id": uid, "title": title, "text": _normalize_text(entries_txt), "raw": cal})
    return items


def _index_inventory() -> List[Dict[str, Any]]:
    items = []
    for iid, r in _input_inventory_store.items():
        title = r.get("name") or iid
        text = " ".join(filter(None, [title, str(r.get("item_id")), str(r.get("quantity")), str(r.get("unit"))]))
        items.append({"type": "inventory", "id": iid, "title": title, "text": _normalize_text(text), "raw": r})
    return items


def _index_ledger() -> List[Dict[str, Any]]:
    items = []
    for e in (_ledger_store or []):
        eid = e.get("entry_id")
        title = f"{e.get('type')} {e.get('category')} {e.get('amount')}"
        text = " ".join(filter(None, [e.get("description") or "", e.get("category") or "", e.get("tags") and " ".join(e.get("tags")) or ""]))
        items.append({"type": "ledger", "id": eid, "title": title, "text": _normalize_text(text), "raw": e})
    return items


def _index_peers() -> List[Dict[str, Any]]:
    items = []
    for pid, p in _peer_store.items():
        title = p.get("name") or pid
        text = " ".join(filter(None, [title, str(p.get("location") or ""), str(p.get("metrics") or "")]))
        items.append({"type": "peer", "id": pid, "title": title, "text": _normalize_text(text), "raw": p})
    return items


def _index_recommendations(unit_id: Optional[str] = None) -> List[Dict[str, Any]]:
    items = []
    if not generate_recommendations_for_unit:
        return items
    # if unit provided, index only that unit's recommendations; otherwise index all units
    units = [unit_id] if unit_id else list(_unit_store.keys())
    for uid in units:
        try:
            r = generate_recommendations_for_unit(uid)
            for idx, rec in enumerate(r.get("recommendations", [])):
                rid = f"{uid}__rec__{idx}"
                title = rec.get("category") + ": " + (rec.get("recommendation") or "")[:60]
                text = " ".join(filter(None, [rec.get("recommendation") or "", str(rec.get("meta") or "")]))
                items.append({"type": "recommendation", "id": rid, "title": title, "text": _normalize_text(text), "raw": rec, "unit_id": uid})
        except Exception:
            continue
    return items


# ---------- Main search function ----------
def unified_search(
    query: str,
    types: Optional[List[str]] = None,
    unit_id: Optional[str] = None,
    page: int = 1,
    per_page: int = 20
) -> Dict[str, Any]:
    """
    query: search text (required)
    types: optional list to restrict to ['unit','task_template','alert','calendar','inventory','ledger','peer','recommendation']
    unit_id: optional to restrict recommendations/calendar/units to a particular unit
    pagination: page, per_page
    """

    q = _normalize_text(query)
    if not q:
        return {"query": query, "total": 0, "hits": [], "page": page, "per_page": per_page}

    # build index based on requested types
    index: List[Dict[str, Any]] = []

    requested = set([t.strip().lower() for t in (types or [])]) if types else None

    def allow(tname: str):
        return (requested is None) or (tname in requested)

    if allow("unit"):
        index.extend(_index_units())
    if allow("task_template"):
        index.extend(_index_tasks())
    if allow("alert"):
        index.extend(_index_alerts())
    if allow("calendar"):
        index.extend(_index_calendars())
    if allow("inventory"):
        index.extend(_index_inventory())
    if allow("ledger"):
        index.extend(_index_ledger())
    if allow("peer"):
        index.extend(_index_peers())
    if allow("recommendation"):
        index.extend(_index_recommendations(unit_id=unit_id))

    # scoring
    hits: List[Tuple[float, Dict[str, Any]]] = []
    for item in index:
        text = item.get("text", "")
        title = _normalize_text(item.get("title", ""))
        # compute best of title and text
        s_title = _score_match(q, title)
        s_text = _score_match(q, text)
        score = max(s_title * 1.1, s_text)  # small boost for title matches
        if score <= 0:
            continue
        snippet = _build_snippet(query, (item.get("raw") and str(item.get("raw")) ) or title)
        hit = {
            "type": item.get("type"),
            "id": item.get("id"),
            "title": item.get("title"),
            "score": score,
            "snippet": snippet,
            "raw": item.get("raw")
        }
        # include unit_id for recommendations
        if item.get("type") == "recommendation" and item.get("unit_id"):
            hit["unit_id"] = item.get("unit_id")
        hits.append((score, hit))

    # sort by score desc
    hits_sorted = [h for _, h in sorted(hits, key=lambda x: x[0], reverse=True)]

    total = len(hits_sorted)
    # pagination
    start = max(0, (page - 1) * per_page)
    end = start + per_page
    page_hits = hits_sorted[start:end]

    return {"query": query, "total": total, "page": page, "per_page": per_page, "hits": page_hits}
