# backend/app/services/farmer/offline_sync_service.py

from datetime import datetime
from threading import Lock
from typing import Dict, Any, List, Optional
import uuid
import copy

"""
Offline Sync Engine (in-memory)

Concepts:
 - device registry: devices that will sync
 - operation queue: per-device list of client operations (batched pushes)
 - each op: {
     op_id: str,
     entity: "unit" | "calendar" | "ledger" | "inventory" | ...,
     entity_id: str (optional for create),
     action: "create"|"update"|"delete",
     payload: dict,
     client_ts: ISO str (client local time),
     server_received_at: ISO str (set on receive)
   }
 - change log / versions: we use server-side last_modified ISO timestamps per entity (if present)
 - conflict detection: if server's last_modified > client's client_ts and server state differs, report conflict
 - resolution: client may accept server version, accept client version (force), or supply merged payload
"""

_lock = Lock()

# device_id -> { device_id, farmer_id (optional), last_sync_iso, registered_at }
_devices: Dict[str, Dict[str, Any]] = {}

# device op queues (device_id -> [op, ...])
_device_queues: Dict[str, List[Dict[str, Any]]] = {}

# Simplified server entity last-mod times (entity_type::entity_id -> iso)
_entity_last_modified: Dict[str, str] = {}

# For best-effort apply we import common in-memory stores (best-effort)
try:
    from app.services.farmer.unit_service import _unit_store
except Exception:
    _unit_store = {}

try:
    from app.services.farmer.season_calendar_service import _calendar_store
except Exception:
    _calendar_store = {}

try:
    from app.services.farmer.financial_ledger_service import _ledger_store
except Exception:
    _ledger_store = []

try:
    from app.services.farmer.input_shortage_service import _input_inventory_store
except Exception:
    _input_inventory_store = {}

# helper
def _now_iso() -> str:
    return datetime.utcnow().isoformat()


def register_device(device_id: Optional[str] = None, farmer_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Register or refresh a device.
    Returns device record.
    """
    if not device_id:
        device_id = f"dev_{uuid.uuid4()}"
    rec = {
        "device_id": device_id,
        "farmer_id": farmer_id,
        "last_sync_iso": None,
        "registered_at": _now_iso()
    }
    with _lock:
        _devices[device_id] = rec
        _device_queues.setdefault(device_id, [])
    return rec


def get_device(device_id: str) -> Dict[str, Any]:
    with _lock:
        return _devices.get(device_id, {})


def list_devices() -> List[Dict[str, Any]]:
    with _lock:
        return list(_devices.values())


def push_operations(device_id: str, ops: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Accept a batch of client ops from device.
    Each op must include: {entity, action, payload, entity_id (optional), client_ts}
    Server will append to device queue, set server_received_at, attempt best-effort apply and detect conflicts.
    Returns:
      {accepted_ops: [...], conflicts: [...], applied: [...], queued_count: int}
    """
    if device_id not in _device_queues:
        return {"error": "device_not_registered"}

    accepted = []
    conflicts = []
    applied = []

    with _lock:
        queue = _device_queues[device_id]
        for op in ops:
            oprec = {
                "op_id": op.get("op_id") or f"op_{uuid.uuid4()}",
                "device_id": device_id,
                "entity": op.get("entity"),
                "entity_id": op.get("entity_id"),
                "action": op.get("action"),
                "payload": op.get("payload"),
                "client_ts": op.get("client_ts"),
                "server_received_at": _now_iso()
            }

            # Detect conflict heuristically:
            key = f"{oprec['entity']}::{oprec.get('entity_id') or oprec['op_id']}"
            server_last = _entity_last_modified.get(key)
            client_ts = None
            try:
                client_ts = oprec.get("client_ts")
            except Exception:
                client_ts = None

            # get current server state (best-effort per entity)
            current = None
            if oprec["entity"] == "unit":
                current = copy.deepcopy(_unit_store.get(oprec.get("entity_id")))
            elif oprec["entity"] == "calendar":
                current = copy.deepcopy(_calendar_store.get(oprec.get("entity_id")))
            elif oprec["entity"] == "ledger":
                # ledger is a list; we check if entry exists by id
                for e in _ledger_store:
                    if e.get("entry_id") == oprec.get("entity_id"):
                        current = copy.deepcopy(e); break
            elif oprec["entity"] == "inventory":
                current = copy.deepcopy(_input_inventory_store.get(oprec.get("entity_id")))

            # conflict if server_last exists and server_last > client_ts and payload differs
            is_conflict = False
            if server_last and client_ts:
                try:
                    if server_last > client_ts:
                        # payload compare simple: string compare; if different -> conflict
                        if oprec["payload"] is not None and current is not None:
                            # normalized compare
                            import json
                            try:
                                server_s = json.dumps(current, sort_keys=True)
                                client_s = json.dumps(oprec["payload"], sort_keys=True)
                                if server_s != client_s:
                                    is_conflict = True
                            except Exception:
                                # fallback — if current differs at all
                                if current != oprec["payload"]:
                                    is_conflict = True
                        else:
                            # server changed but no comparable payload -> mark conflict
                            is_conflict = True
                except Exception:
                    is_conflict = False

            if is_conflict:
                conflicts.append({"op": oprec, "server_state": current, "server_last_modified": server_last})
                # still enqueue so operator can resolve later if desired
                queue.append(oprec)
            else:
                # apply immediately (best-effort) and record last modified
                applied_flag = False
                try:
                    if oprec["entity"] == "unit":
                        eid = oprec.get("entity_id") or oprec["payload"].get("unit_id") or f"unit_{uuid.uuid4()}"
                        _unit_store[eid] = oprec["payload"]
                        _entity_last_modified[f"unit::{eid}"] = oprec["server_received_at"]
                        oprec["entity_id"] = eid
                        applied_flag = True
                    elif oprec["entity"] == "calendar":
                        eid = oprec.get("entity_id") or oprec["payload"].get("unit_id")
                        if eid:
                            _calendar_store[eid] = oprec["payload"]
                            _entity_last_modified[f"calendar::{eid}"] = oprec["server_received_at"]
                            oprec["entity_id"] = eid
                            applied_flag = True
                    elif oprec["entity"] == "ledger":
                        # payload should be ledger entry dict with entry_id
                        entry = oprec["payload"]
                        if entry:
                            _ledger_store.append(entry)
                            _entity_last_modified[f"ledger::{entry.get('entry_id')}"] = oprec["server_received_at"]
                            oprec["entity_id"] = entry.get("entry_id")
                            applied_flag = True
                    elif oprec["entity"] == "inventory":
                        iid = oprec.get("entity_id") or oprec["payload"].get("item_id")
                        if iid:
                            _input_inventory_store[iid] = oprec["payload"]
                            _entity_last_modified[f"inventory::{iid}"] = oprec["server_received_at"]
                            oprec["entity_id"] = iid
                            applied_flag = True
                    else:
                        # unknown entity: just enqueue (pass-through)
                        queue.append(oprec)
                except Exception:
                    queue.append(oprec)

                if applied_flag:
                    applied.append(oprec)
                else:
                    accepted.append(oprec)

        # update queue length
        _device_queues[device_id] = queue

    # Return summary
    return {"accepted_ops": [a.get("op_id") for a in accepted], "applied_ops": [a.get("op_id") for a in applied], "conflicts": conflicts, "queued_count": len(_device_queues[device_id])}


def pull_server_changes(device_id: str, since_iso: Optional[str] = None, limit: int = 100) -> Dict[str, Any]:
    """
    Return server-side changes since `since_iso`.
    For simplicity we return entity snapshots where last_modified > since_iso.
    """
    if device_id not in _devices:
        return {"error": "device_not_registered"}

    since = since_iso or "1970-01-01T00:00:00"
    changes = []

    with _lock:
        for key, ts in _entity_last_modified.items():
            try:
                if ts > since:
                    # key example: entity::entity_id
                    parts = key.split("::", 1)
                    if len(parts) != 2:
                        continue
                    entity, eid = parts
                    snapshot = None
                    if entity == "unit":
                        snapshot = copy.deepcopy(_unit_store.get(eid))
                    elif entity == "calendar":
                        snapshot = copy.deepcopy(_calendar_store.get(eid))
                    elif entity == "ledger":
                        # find entry
                        for e in _ledger_store:
                            if e.get("entry_id") == eid:
                                snapshot = copy.deepcopy(e); break
                    elif entity == "inventory":
                        snapshot = copy.deepcopy(_input_inventory_store.get(eid))
                    change = {"entity": entity, "entity_id": eid, "last_modified": ts, "snapshot": snapshot}
                    changes.append(change)
            except Exception:
                continue

    # sort by last_modified ascending
    changes_sorted = sorted(changes, key=lambda x: x.get("last_modified"))
    return {"since": since, "changes": changes_sorted[:limit], "count": len(changes_sorted[:limit])}


def list_device_queue(device_id: str) -> Dict[str, Any]:
    if device_id not in _device_queues:
        return {"error": "device_not_registered"}
    with _lock:
        return {"device_id": device_id, "queue": list(_device_queues[device_id])}


def resolve_conflict(device_id: str, op_id: str, resolution: Dict[str, Any]) -> Dict[str, Any]:
    """
    resolution: { action: "accept_server"|"accept_client"|"merge", merged_payload: {...} (if merge) }
    If accept_client -> force-apply client payload and update last_modified
    If accept_server -> drop op from queue
    If merge -> apply merged_payload and update last_modified
    """
    if device_id not in _device_queues:
        return {"error": "device_not_registered"}
    with _lock:
        queue = _device_queues[device_id]
        target = None
        for idx, op in enumerate(queue):
            if op.get("op_id") == op_id:
                target = (idx, op)
                break
        if not target:
            return {"error": "op_not_found"}
        idx, oprec = target

        res_action = resolution.get("action")
        if res_action == "accept_server":
            # remove op from queue
            queue.pop(idx)
            _device_queues[device_id] = queue
            return {"status": "accepted_server", "op_id": op_id}
        elif res_action == "accept_client":
            # force apply client's payload overwriting server state
            entity = oprec.get("entity"); eid = oprec.get("entity_id")
            ts = _now_iso()
            try:
                if entity == "unit":
                    _unit_store[eid] = oprec.get("payload")
                    _entity_last_modified[f"unit::{eid}"] = ts
                elif entity == "calendar":
                    _calendar_store[eid] = oprec.get("payload")
                    _entity_last_modified[f"calendar::{eid}"] = ts
                elif entity == "ledger":
                    _ledger_store.append(oprec.get("payload"))
                    _entity_last_modified[f"ledger::{oprec.get('payload',{}).get('entry_id')}"] = ts
                elif entity == "inventory":
                    _input_inventory_store[eid] = oprec.get("payload")
                    _entity_last_modified[f"inventory::{eid}"] = ts
                # remove op from queue
                queue.pop(idx)
                _device_queues[device_id] = queue
                return {"status": "applied_client", "op_id": op_id}
            except Exception as e:
                return {"error": "apply_failed", "details": str(e)}
        elif res_action == "merge":
            merged = resolution.get("merged_payload")
            if not merged:
                return {"error": "missing_merged_payload"}
            entity = oprec.get("entity"); eid = oprec.get("entity_id")
            ts = _now_iso()
            try:
                if entity == "unit":
                    _unit_store[eid] = merged
                    _entity_last_modified[f"unit::{eid}"] = ts
                elif entity == "calendar":
                    _calendar_store[eid] = merged
                    _entity_last_modified[f"calendar::{eid}"] = ts
                elif entity == "ledger":
                    _ledger_store.append(merged)
                    _entity_last_modified[f"ledger::{merged.get('entry_id')}"] = ts
                elif entity == "inventory":
                    _input_inventory_store[eid] = merged
                    _entity_last_modified[f"inventory::{eid}"] = ts
                queue.pop(idx)
                _device_queues[device_id] = queue
                return {"status": "merged_and_applied", "op_id": op_id}
            except Exception as e:
                return {"error": "merge_failed", "details": str(e)}
        else:
            return {"error": "unknown_resolution_action"}


def purge_device_queue(device_id: str) -> Dict[str, Any]:
    if device_id not in _device_queues:
        return {"error": "device_not_registered"}
    with _lock:
        _device_queues[device_id] = []
    return {"status": "purged", "device_id": device_id}
