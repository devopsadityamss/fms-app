# backend/app/api/farmer/data_export.py

from fastapi import APIRouter, HTTPException
from typing import Optional

from app.services.farmer.data_export_service import export_data

router = APIRouter()


@router.get("/export")
def api_export(
    format: str,
    unit_id: Optional[str] = None
):
    result = export_data(format, unit_id)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result
