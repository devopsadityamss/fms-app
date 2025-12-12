"""
Worker Instructions Broadcast Service (stub-ready)
--------------------------------------------------

Allows the farm owner to broadcast instructions to:
 - all workers
 - a selected set of workers
 - workers assigned to a specific production unit

Each broadcast includes:
 - title
 - message
 - target: ALL | worker_ids | unit_id
 - created_at
 - optional expires_at
 - delivery_status (stub)

This module does NOT send real notifications.
Integration with SMS/push/WhatsApp can be added later.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
import uuid


# ---------------------------------------------------------------------
# In-memory store
# ---------------------------------------------------------------------
_instruction_store: Dict[str, Dict[str, Any]] = {}


def _new_id() -> str:
    return str(uuid.uuid4())


def _now() -> str:
    return datetime.utcnow().isoformat()


# ---------------------------------------------------------------------
# Helper: determine target structure
# ---------------------------------------------------------------------
def _build_target(target_all: bool, worker_ids: Optional[List[str]], unit_id: Optional[str]) -> Dict[str, Any]:
    if target_all:
        return {"mode": "all"}
    if worker_ids:
        return {"mode": "workers", "workers": worker_ids}
    if unit_id:
        return {"mode": "unit", "unit_id": unit_id}
    return {"mode": "all"}  # default fallback


# ---------------------------------------------------------------------
# Create broadcast instruction
# ---------------------------------------------------------------------
def create_instruction(
    title: str,
    message: str,
    target_all: bool,
    worker_ids: Optional[List[str]],
    unit_id: Optional[str],
    expires_at: Optional[str],
    notes: Optional[str] = None
) -> Dict[str, Any]:

    instr_id = _new_id()
    target = _build_target(target_all, worker_ids, unit_id)

    record = {
        "id": instr_id,
        "title": title,
        "message": message,
        "target": target,   # structured target
        "notes": notes,
        "created_at": _now(),
        "expires_at": expires_at,
        # Stub: delivery_status is static; in real system this will update as messages get delivered.
        "delivery_status": "not_delivered",  # pending | delivered (stub)
    }

    _instruction_store[instr_id] = record
    return record


# ---------------------------------------------------------------------
# Get instruction
# ---------------------------------------------------------------------
def get_instruction(instr_id: str) -> Optional[Dict[str, Any]]:
    return _instruction_store.get(instr_id)


# ---------------------------------------------------------------------
# List instructions
# ---------------------------------------------------------------------
def list_instructions(
    mode: Optional[str] = None,   # all/workers/unit
    worker_id: Optional[str] = None,
    unit_id: Optional[str] = None
) -> Dict[str, Any]:

    items = list(_instruction_store.values())

    if mode:
        items = [i for i in items if i["target"]["mode"] == mode]

    if worker_id:
        items = [
            i for i in items
            if i["target"]["mode"] == "workers" and worker_id in i["target"].get("workers", [])
        ]

    if unit_id:
        items = [
            i for i in items
            if i["target"]["mode"] == "unit" and i["target"].get("unit_id") == unit_id
        ]

    return {"count": len(items), "items": items}


# ---------------------------------------------------------------------
# Delete instruction
# ---------------------------------------------------------------------
def delete_instruction(instr_id: str) -> bool:
    if instr_id in _instruction_store:
        del _instruction_store[instr_id]
        return True
    return False


# ---------------------------------------------------------------------
# Stub: mark delivered (manual)
# ---------------------------------------------------------------------
def mark_delivered(instr_id: str) -> Optional[Dict[str, Any]]:
    rec = _instruction_store.get(instr_id)
    if not rec:
        return None
    rec["delivery_status"] = "delivered"
    _instruction_store[instr_id] = rec
    return rec


def _clear_store():
    _instruction_store.clear()
