# backend/app/services/farmer/harvest_lot_service.py
"""
Harvest Lot Management (Feature 331)

- Create harvest lot (from unit harvest event or manually)
- Link to seed/input batches or units
- Record quality tests (moisture, dockage, grade)
- Compute simple quality score
- Assign storage (silo/warehouse)
- Transfer / reserve / release lots
- Export CSV summary
"""

from datetime import datetime
from threading import Lock
from typing import Dict, Any, List, Optional
import uuid
import io
import csv
import statistics

# defensive imports (best-effort)
try:
    from app.services.farmer.seed_service import get_seed_batch
except Exception:
    get_seed_batch = lambda batch_id: {}

try:
    from app.services.farmer.unit_service import _unit_store
except Exception:
    _unit_store = {}

_lock = Lock()

_lots: Dict[str, Dict[str, Any]] = {}           # lot_id -> record
_lots_by_farmer: Dict[str, List[str]] = {}      # farmer_id -> [lot_id]
_lots_by_unit: Dict[str, List[str]] = {}        # unit_id -> [lot_id]
_quality_tests: Dict[str, List[Dict[str, Any]]] = {}  # lot_id -> [tests]
_storage_assignments: Dict[str, Dict[str, Any]] = {}  # lot_id -> storage record
_transfers: Dict[str, Dict[str, Any]] = {}      # transfer_id -> record

def _now_iso():
    return datetime.utcnow().isoformat()

def _uid(prefix="lot"):
    return f"{prefix}_{uuid.uuid4()}"

# -----------------------
# CRUD
# -----------------------
def create_harvest_lot(
    farmer_id: str,
    unit_id: Optional[str],
    crop: str,
    harvested_qty_kg: float,
    harvest_date_iso: Optional[str] = None,
    seed_batch_id: Optional[str] = None,
    moisture_pct: Optional[float] = None,
    initial_quality_notes: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    lid = _uid("hl")
    rec = {
        "lot_id": lid,
        "farmer_id": farmer_id,
        "unit_id": unit_id,
        "crop": crop,
        "harvested_qty_kg": float(harvested_qty_kg),
        "available_qty_kg": float(harvested_qty_kg),
        "harvest_date": harvest_date_iso or datetime.utcnow().date().isoformat(),
        "seed_batch_id": seed_batch_id,
        "initial_moisture_pct": float(moisture_pct) if moisture_pct is not None else None,
        "initial_quality_notes": initial_quality_notes or "",
        "metadata": metadata or {},
        "created_at": _now_iso(),
        "updated_at": None,
        "status": "created"  # created | stored | moved | consumed
    }

    with _lock:
        _lots[lid] = rec
        _lots_by_farmer.setdefault(farmer_id, []).append(lid)
        if unit_id:
            _lots_by_unit.setdefault(str(unit_id), []).append(lid)
    return rec

def get_harvest_lot(lot_id: str) -> Dict[str, Any]:
    with _lock:
        rec = _lots.get(lot_id)
        return rec.copy() if rec else {}

def list_lots_by_farmer(farmer_id: str) -> List[Dict[str, Any]]:
    with _lock:
        ids = _lots_by_farmer.get(farmer_id, [])
        return [_lots[i].copy() for i in ids]

def list_lots_by_unit(unit_id: str) -> List[Dict[str, Any]]:
    with _lock:
        ids = _lots_by_unit.get(str(unit_id), [])
        return [_lots[i].copy() for i in ids]

def update_harvest_lot(lot_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
    with _lock:
        rec = _lots.get(lot_id)
        if not rec:
            return {"error": "not_found"}
        # careful updates: numeric casts
        if "harvested_qty_kg" in updates:
            try:
                new_qty = float(updates["harvested_qty_kg"])
                delta = new_qty - rec.get("harvested_qty_kg", 0.0)
                rec["harvested_qty_kg"] = new_qty
                rec["available_qty_kg"] = max(0.0, rec.get("available_qty_kg", 0.0) + delta)
            except Exception:
                pass
        for k in ("crop","harvest_date","seed_batch_id","initial_quality_notes","status"):
            if k in updates:
                rec[k] = updates[k]
        rec["metadata"].update(updates.get("metadata", {}) or {})
        rec["updated_at"] = _now_iso()
        _lots[lot_id] = rec
        return rec.copy()

def delete_harvest_lot(lot_id: str) -> Dict[str, Any]:
    with _lock:
        rec = _lots.pop(lot_id, None)
        if not rec:
            return {"error": "not_found"}
        farmer_id = rec.get("farmer_id")
        unit_id = rec.get("unit_id")
        if farmer_id and farmer_id in _lots_by_farmer:
            _lots_by_farmer[farmer_id] = [i for i in _lots_by_farmer[farmer_id] if i != lot_id]
        if unit_id and str(unit_id) in _lots_by_unit:
            _lots_by_unit[str(unit_id)] = [i for i in _lots_by_unit[str(unit_id)] if i != lot_id]
        _quality_tests.pop(lot_id, None)
        _storage_assignments.pop(lot_id, None)
    return {"status": "deleted", "lot_id": lot_id}

# -----------------------
# Create lot from harvest event helper
# -----------------------
def create_lot_from_harvest_event(
    farmer_id: str,
    unit_id: str,
    crop: str,
    harvested_qty_kg: float,
    harvest_date_iso: Optional[str] = None,
    seed_batch_id: Optional[str] = None,
    moisture_pct: Optional[float] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Short helper used when a harvest is recorded in task/stage completion: create a harvest lot with basic fields.
    """
    return create_harvest_lot(
        farmer_id=farmer_id,
        unit_id=unit_id,
        crop=crop,
        harvested_qty_kg=harvested_qty_kg,
        harvest_date_iso=harvest_date_iso,
        seed_batch_id=seed_batch_id,
        moisture_pct=moisture_pct,
        metadata=metadata
    )

# -----------------------
# Quality tests & scoring
# -----------------------
def record_quality_test(
    lot_id: str,
    tester: Optional[str],
    moisture_pct: Optional[float] = None,
    dockage_pct: Optional[float] = None,
    grade: Optional[str] = None,
    protein_pct: Optional[float] = None,
    notes: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    with _lock:
        if lot_id not in _lots:
            return {"error": "lot_not_found"}
    rec = {
        "test_id": _uid("qt"),
        "lot_id": lot_id,
        "tester": tester or "",
        "moisture_pct": float(moisture_pct) if moisture_pct is not None else None,
        "dockage_pct": float(dockage_pct) if dockage_pct is not None else None,
        "grade": grade or "",
        "protein_pct": float(protein_pct) if protein_pct is not None else None,
        "notes": notes or "",
        "metadata": metadata or {},
        "recorded_at": _now_iso()
    }
    with _lock:
        _quality_tests.setdefault(lot_id, []).append(rec)
    return rec

def list_quality_tests(lot_id: str) -> List[Dict[str, Any]]:
    with _lock:
        return list(_quality_tests.get(lot_id, []))

def compute_lot_quality_score(lot_id: str) -> Dict[str, Any]:
    """
    Heuristic score: start at 100, penalize by moisture and dockage; bonus for protein and grade keywords.
    Returns {'lot_id', 'score', 'components'}
    """
    tests = list_quality_tests(lot_id)
    if not tests:
        return {"lot_id": lot_id, "score": None, "components": {}, "reason": "no_tests"}

    moist_vals = [t["moisture_pct"] for t in tests if t.get("moisture_pct") is not None]
    dock_vals = [t["dockage_pct"] for t in tests if t.get("dockage_pct") is not None]
    prot_vals = [t["protein_pct"] for t in tests if t.get("protein_pct") is not None]
    grades = [t.get("grade","").lower() for t in tests if t.get("grade")]

    score = 100.0
    components = {}

    if moist_vals:
        avg_moist = statistics.mean(moist_vals)
        # ideal moisture varies; assume ideal <=12
        moist_penalty = max(0.0, (avg_moist - 12.0) * 3.0)  # 3 points per % above 12
        score -= moist_penalty
        components["avg_moisture_pct"] = round(avg_moist,2)
        components["moisture_penalty"] = round(moist_penalty,2)

    if dock_vals:
        avg_dock = statistics.mean(dock_vals)
        dock_penalty = avg_dock * 1.5  # 1.5 points per % dockage
        score -= dock_penalty
        components["avg_dockage_pct"] = round(avg_dock,2)
        components["dockage_penalty"] = round(dock_penalty,2)

    if prot_vals:
        avg_prot = statistics.mean(prot_vals)
        prot_bonus = max(0.0, (avg_prot - 10.0) * 1.0)  # small bonus above 10%
        score += prot_bonus
        components["avg_protein_pct"] = round(avg_prot,2)
        components["protein_bonus"] = round(prot_bonus,2)

    # grade boost/penalty (mock)
    grade_score_adj = 0.0
    for g in grades:
        if "premium" in g or "a+" in g or "grade_a" in g:
            grade_score_adj += 5.0
        if "b" in g and grade_score_adj == 0.0:
            grade_score_adj -= 3.0
    if grade_score_adj:
        score += grade_score_adj
        components["grade_adjustment"] = round(grade_score_adj,2)

    score = max(0.0, min(100.0, round(score,2)))
    components["final_score"] = score
    return {"lot_id": lot_id, "score": score, "components": components}

# -----------------------
# Storage & transfers
# -----------------------
def assign_storage(lot_id: str, storage_id: str, location_name: Optional[str] = None, stored_at_iso: Optional[str] = None):
    with _lock:
        rec = _lots.get(lot_id)
        if not rec:
            return {"error": "lot_not_found"}
        storage = {
            "lot_id": lot_id,
            "storage_id": storage_id,
            "location_name": location_name or "",
            "stored_at": stored_at_iso or _now_iso()
        }
        _storage_assignments[lot_id] = storage
        rec["status"] = "stored"
        rec["updated_at"] = _now_iso()
        _lots[lot_id] = rec
    return storage

def get_storage_assignment(lot_id: str) -> Dict[str, Any]:
    with _lock:
        return _storage_assignments.get(lot_id, {}).copy()

def transfer_lot(lot_id: str, to_storage_id: str, moved_by: Optional[str] = None, notes: Optional[str] = None):
    with _lock:
        if lot_id not in _lots:
            return {"error": "lot_not_found"}
        prev = _storage_assignments.get(lot_id)
        tid = _uid("tx")
        rec = {
            "transfer_id": tid,
            "lot_id": lot_id,
            "from_storage": prev.get("storage_id") if prev else None,
            "to_storage": to_storage_id,
            "moved_by": moved_by,
            "notes": notes or "",
            "transferred_at": _now_iso()
        }
        _transfers[tid] = rec
        # update storage assignment
        _storage_assignments[lot_id] = {"lot_id": lot_id, "storage_id": to_storage_id, "location_name": "", "stored_at": _now_iso()}
        # mark lot status
        rec_lot = _lots[lot_id]
        rec_lot["status"] = "moved"
        rec_lot["updated_at"] = _now_iso()
        _lots[lot_id] = rec_lot
    return rec

def list_transfers_for_lot(lot_id: str) -> List[Dict[str, Any]]:
    with _lock:
        return [v for v in _transfers.values() if v.get("lot_id") == lot_id]

# -----------------------
# Allocation / consume
# -----------------------
def allocate_from_lot(lot_id: str, qty_kg: float, purpose: Optional[str] = None):
    with _lock:
        if lot_id not in _lots:
            return {"error": "lot_not_found"}
        rec = _lots[lot_id]
        if rec.get("available_qty_kg", 0.0) < float(qty_kg):
            return {"error": "insufficient_quantity", "available_qty_kg": rec.get("available_qty_kg", 0.0)}
        rec["available_qty_kg"] = round(rec["available_qty_kg"] - float(qty_kg), 3)
        rec["updated_at"] = _now_iso()
        _lots[lot_id] = rec
    return {"lot_id": lot_id, "allocated_kg": float(qty_kg), "remaining_kg": rec["available_qty_kg"], "purpose": purpose}

# -----------------------
# Export
# -----------------------
def export_lots_csv(farmer_id: str) -> str:
    lots = list_lots_by_farmer(farmer_id)
    out = io.StringIO()
    w = csv.writer(out)
    w.writerow(["lot_id","crop","harvest_date","harvested_qty_kg","available_qty_kg","seed_batch_id","status","created_at"])
    for l in lots:
        w.writerow([l.get("lot_id"), l.get("crop"), l.get("harvest_date"), l.get("harvested_qty_kg"), l.get("available_qty_kg"), l.get("seed_batch_id"), l.get("status"), l.get("created_at")])
    return out.getvalue()
