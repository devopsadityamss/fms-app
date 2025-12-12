"""
API Routes — Skill Matrix
-------------------------

Endpoints:
 - POST   /farmer/skills
 - GET    /farmer/skills/{skill_id}
 - PUT    /farmer/skills/{skill_id}
 - DELETE /farmer/skills/{skill_id}
 - GET    /farmer/skills                (list all or for worker_id)
 - GET    /farmer/skills/search         (find workers for skill)
 - POST   /farmer/skills/gap            (gap analysis)
"""

from fastapi import APIRouter, HTTPException, Query, Body
from typing import Dict, Any, Optional, List

from app.services.farmer import skill_matrix_service as svc

router = APIRouter()


@router.post("/farmer/skills")
async def api_add_skill(payload: Dict[str, Any] = Body(...)):
    required = ["worker_id", "skill", "proficiency"]
    for r in required:
        if r not in payload:
            raise HTTPException(status_code=400, detail=f"{r} is required")

    return svc.add_skill(
        worker_id=payload["worker_id"],
        skill_name=payload["skill"],
        proficiency=payload["proficiency"],
        certifications=payload.get("certifications"),
        training=payload.get("training"),
        notes=payload.get("notes")
    )


@router.get("/farmer/skills/{skill_id}")
def api_get_skill(skill_id: str):
    rec = svc.get_skill(skill_id)
    if not rec:
        raise HTTPException(status_code=404, detail="skill_not_found")
    return rec


@router.put("/farmer/skills/{skill_id}")
async def api_update_skill(skill_id: str, payload: Dict[str, Any] = Body(...)):
    rec = svc.update_skill(skill_id, payload)
    if not rec:
        raise HTTPException(status_code=404, detail="skill_not_found")
    return rec


@router.delete("/farmer/skills/{skill_id}")
def api_delete_skill(skill_id: str):
    ok = svc.delete_skill(skill_id)
    if not ok:
        raise HTTPException(status_code=404, detail="skill_not_found")
    return {"success": True}


@router.get("/farmer/skills")
def api_list_skills(worker_id: Optional[str] = Query(None)):
    return svc.list_skills(worker_id)


@router.get("/farmer/skills/search")
def api_search_skills(
    skill_name: str = Query(...),
    min_proficiency: str = Query("beginner")
):
    return svc.find_workers_for_skill(skill_name, min_proficiency)


@router.post("/farmer/skills/gap")
async def api_gap_analysis(payload: Dict[str, Any] = Body(...)):
    required = ["worker_id", "required_skills"]
    for r in required:
        if r not in payload:
            raise HTTPException(status_code=400, detail=f"{r} is required")

    return svc.skill_gap_for_task(
        required_skills=payload["required_skills"],
        worker_id=payload["worker_id"]
    )
