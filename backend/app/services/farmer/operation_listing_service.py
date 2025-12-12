"""
Operation Listing Service (stub-ready)
--------------------------------------

Responsibilities:
 - Keep an in-memory store of operations (create/read/list/update/delete)
 - Provide simple filters (by unit_id, by status, by operation_type)
 - Provide light-weight summaries / counts
 - Provide a hook for more advanced scheduling / recommendations later

Notes:
 - Everything is in-memory for now. Replace the _store with a DB-backed layer later.
 - Keep function signatures stable so API doesn't change when internals switch.
"""

from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
import uuid

# In-memory store: operation_id -> operation record
_operation_store: Dict[str, Dict[str, Any]] = {}

# ----- helpers --------------------------------------------------------------
def _now_iso() -> str:
    return datetime.utcnow().isoformat()

def _new_id() -> str:
    return str(uuid.uuid4())

# ----- core CRUD ------------------------------------------------------------
def create_operation(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create a new operation record.
    Expected payload keys (examples): unit_id, operation_type, scheduled_at, operator, notes, status
    """
    op_id = _new_id()
    record = {
        "id": op_id,
        "unit_id": payload.get("unit_id"),
        "operation_type": payload.get("operation_type", "unspecified"),
        "scheduled_at": payload.get("scheduled_at"),  # ISO str or None
        "operator": payload.get("operator"),
        "notes": payload.get("notes"),
        "status": payload.get("status", "planned"),  # planned | in_progress | completed | cancelled
        "meta": payload.get("meta", {}),
        "created_at": _now_iso(),
        "updated_at": _now_iso(),
    }
    _operation_store[op_id] = record
    return record

def get_operation(op_id: str) -> Optional[Dict[str, Any]]:
    return _operation_store.get(op_id)

def update_operation(op_id: str, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    rec = _operation_store.get(op_id)
    if not rec:
        return None
    # update allowed fields
    for k in ("unit_id", "operation_type", "scheduled_at", "operator", "notes", "status", "meta"):
        if k in payload:
            rec[k] = payload[k]
    rec["updated_at"] = _now_iso()
    _operation_store[op_id] = rec
    return rec

def delete_operation(op_id: str) -> bool:
    if op_id in _operation_store:
        del _operation_store[op_id]
        return True
    return False

# ----- listing / filtering / pagination -------------------------------------
def list_operations(
    unit_id: Optional[str] = None,
    operation_type: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    sort_desc: bool = True
) -> Dict[str, Any]:
    """
    Return a paginated list of operations. Simple list filtering implemented.
    """
    items = list(_operation_store.values())

    # Filters
    if unit_id:
        items = [i for i in items if i.get("unit_id") == unit_id]
    if operation_type:
        items = [i for i in items if i.get("operation_type") == operation_type]
    if status:
        items = [i for i in items if i.get("status") == status]

    # Sort by scheduled_at then created_at
    def _sort_key(i):
        return i.get("scheduled_at") or i.get("created_at") or ""
    items.sort(key=_sort_key, reverse=sort_desc)

    total = len(items)
    paged = items[offset: offset + limit]
    return {"count": total, "items": paged, "limit": limit, "offset": offset}

# ----- domain helpers / stubs ------------------------------------------------
def mark_operation_completed(op_id: str, completion_notes: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """
    Domain-level helper: mark an operation as completed and add notes.
    Stub — can be extended to trigger timeline events, recommendations, or worker payouts.
    """
    rec = _operation_store.get(op_id)
    if not rec:
        return None
    rec["status"] = "completed"
    if completion_notes:
        # append to notes (simple)
        prev = rec.get("notes") or ""
        rec["notes"] = f"{prev}\n[completion_notes] {completion_notes}"
    rec["updated_at"] = _now_iso()
    _operation_store[op_id] = rec
    # Here you can call other services (timeline, recommendations) later
    return rec

def operations_summary_by_unit(unit_id: str) -> Dict[str, int]:
    """
    Quick summary: counts by status for a given unit.
    """
    items = [i for i in _operation_store.values() if i.get("unit_id") == unit_id]
    summary = {}
    for i in items:
        s = i.get("status", "planned")
        summary[s] = summary.get(s, 0) + 1
    return summary

# ----- admin helper (clear store) -------------------------------------------
def _clear_store() -> None:
    """For tests/dev only: wipe the in-memory store."""
    _operation_store.clear()
