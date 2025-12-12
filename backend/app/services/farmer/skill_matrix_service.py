"""
Skill Matrix Service (stub-ready)
---------------------------------

Features:
 - Store skill profiles per worker
 - Each worker has skills with proficiency levels:
       beginner / intermediate / advanced / expert
 - Store certifications and training history
 - Provide skill-based search: find workers who can perform an operation
 - Provide gap analysis: missing skills needed for a task
"""

from typing import Dict, Any, Optional, List
from datetime import datetime
import uuid


_skill_store: Dict[str, Dict[str, Any]] = {}   # skill_id -> record
_worker_index: Dict[str, List[str]] = {}       # worker_id -> list of skill_ids


def _now() -> str:
    return datetime.utcnow().isoformat()


def _new_id() -> str:
    return str(uuid.uuid4())


# -------------------------------------------------------------
# CREATE / UPDATE WORKER SKILL PROFILE
# -------------------------------------------------------------
def add_skill(
    worker_id: str,
    skill_name: str,
    proficiency: str,           # beginner | intermediate | advanced | expert
    certifications: Optional[List[str]] = None,
    training: Optional[List[str]] = None,
    notes: Optional[str] = None
) -> Dict[str, Any]:

    sid = _new_id()

    record = {
        "id": sid,
        "worker_id": worker_id,
        "skill": skill_name,
        "proficiency": proficiency,
        "certifications": certifications or [],
        "training": training or [],
        "notes": notes,
        "created_at": _now(),
        "updated_at": _now()
    }

    _skill_store[sid] = record
    _worker_index.setdefault(worker_id, []).append(sid)
    return record


def update_skill(skill_id: str, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    rec = _skill_store.get(skill_id)
    if not rec:
        return None

    for key in ("skill", "proficiency", "certifications", "training", "notes"):
        if key in payload:
            rec[key] = payload[key]

    rec["updated_at"] = _now()
    return rec


def delete_skill(skill_id: str) -> bool:
    rec = _skill_store.get(skill_id)
    if not rec:
        return False

    worker_id = rec["worker_id"]
    _worker_index[worker_id] = [x for x in _worker_index.get(worker_id, []) if x != skill_id]

    del _skill_store[skill_id]
    return True


def get_skill(skill_id: str) -> Optional[Dict[str, Any]]:
    return _skill_store.get(skill_id)


def list_skills(worker_id: Optional[str] = None) -> Dict[str, Any]:
    if worker_id:
        ids = _worker_index.get(worker_id, [])
        items = [_skill_store[i] for i in ids]
        return {"count": len(items), "items": items}
    else:
        return {"count": len(_skill_store), "items": list(_skill_store.values())}


# -------------------------------------------------------------
# SEARCH SKILLS (FIND WORKERS)
# -------------------------------------------------------------
def find_workers_for_skill(
    skill_name: str,
    min_proficiency: str = "beginner"
) -> Dict[str, Any]:
    """
    Returns all workers who have the skill at ≥ required proficiency.
    Proficiency ranking: beginner < intermediate < advanced < expert
    """

    levels = {
        "beginner": 0,
        "intermediate": 1,
        "advanced": 2,
        "expert": 3
    }

    req_level = levels.get(min_proficiency, 0)
    matches = []

    for rec in _skill_store.values():
        if rec["skill"] != skill_name:
            continue

        if levels.get(rec["proficiency"], 0) >= req_level:
            matches.append(rec)

    return {"count": len(matches), "items": matches}


# -------------------------------------------------------------
# GAP ANALYSIS
# -------------------------------------------------------------
def skill_gap_for_task(
    required_skills: List[str],
    worker_id: str
) -> Dict[str, Any]:
    """
    Compare required skill list with the worker's current skill list.
    Returns missing skills.
    """
    worker_skill_names = [s["skill"] for s in list_skills(worker_id)["items"]]
    missing = [s for s in required_skills if s not in worker_skill_names]

    return {
        "worker_id": worker_id,
        "required_skills": required_skills,
        "missing_skills": missing,
        "gap_count": len(missing)
    }


def _clear_store():
    _skill_store.clear()
    _worker_index.clear()
