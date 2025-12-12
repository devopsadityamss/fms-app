# backend/app/api/farmer/peer_benchmark.py

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict, Any

from app.services.farmer.peer_benchmark_service import (
    register_peer,
    list_peers,
    bulk_import_peers,
    benchmark_unit_against_peers,
    fleet_benchmark_summary
)

router = APIRouter()


class PeerRegisterPayload(BaseModel):
    peer_id: str
    name: str
    location: Optional[str] = None
    metrics: Optional[Dict[str, float]] = None


class BulkImportPayload(BaseModel):
    peers: List[Dict[str, Any]]


@router.post("/peers/register")
def api_register_peer(req: PeerRegisterPayload):
    return register_peer(req.peer_id, req.name, location=req.location, metrics=req.metrics)


@router.get("/peers/list")
def api_list_peers():
    return list_peers()


@router.post("/peers/import")
def api_bulk_import(req: BulkImportPayload):
    return bulk_import_peers(req.peers)


@router.get("/benchmark/unit/{unit_id}")
def api_benchmark_unit(unit_id: str):
    res = benchmark_unit_against_peers(unit_id)
    # If no peers exist, still return unit metrics and note peer_count=0
    return res


@router.get("/benchmark/fleet")
def api_benchmark_fleet():
    return fleet_benchmark_summary()
