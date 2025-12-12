# backend/app/api/farmer/fuel_vendor.py

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

from app.services.farmer.fuel_vendor_service import (
    add_fuel_vendor,
    list_fuel_vendors,
    log_fuel_with_vendor,
    analyze_vendor_for_equipment,
    fleet_vendor_comparison
)

router = APIRouter()


# ----------------------
# Payloads
# ----------------------
class VendorCreate(BaseModel):
    vendor_id: str
    name: str
    location: Optional[str] = None


class VendorFuelLog(BaseModel):
    equipment_id: str
    liters: float
    cost: float
    vendor_id: str
    operator_id: Optional[str] = None
    timestamp: Optional[str] = None


# ----------------------
# Vendor Management
# ----------------------
@router.post("/fuel/vendor")
def api_add_vendor(req: VendorCreate):
    return add_fuel_vendor(req.vendor_id, req.name, req.location)


@router.get("/fuel/vendor/list")
def api_list_vendors():
    return list_fuel_vendors()


# ----------------------
# Vendor-Aware Fuel Log
# ----------------------
@router.post("/fuel/vendor/log")
def api_log_vendor_fuel(req: VendorFuelLog):
    return log_fuel_with_vendor(
        equipment_id=req.equipment_id,
        liters=req.liters,
        cost=req.cost,
        vendor_id=req.vendor_id,
        operator_id=req.operator_id,
        timestamp=req.timestamp
    )


# ----------------------
# Analysis
# ----------------------
@router.get("/fuel/vendor/{equipment_id}/analysis")
def api_vendor_analysis(equipment_id: str):
    return analyze_vendor_for_equipment(equipment_id)


@router.get("/fuel/vendor/fleet")
def api_fleet_vendor():
    return fleet_vendor_comparison()
