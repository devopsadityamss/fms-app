# backend/app/api/farmer/plugin.py

from fastapi import APIRouter, HTTPException
from typing import Dict, Any
from pydantic import BaseModel

from app.services.farmer.plugin_registry_service import (
    register_plugin,
    list_plugins,
    get_plugin,
    unregister_plugin,
    invoke_plugin,
)

router = APIRouter()


class PluginRegisterRequest(BaseModel):
    name: str
    description: str = ""
    version: str = "0.1"
    enabled: bool = True
    # metadata is a free-form dict
    metadata: Dict[str, Any] = {}


@router.post("/plugin/register")
def api_register_plugin(req: PluginRegisterRequest):
    """
    Registers a plugin. For now, handlers are mock-default (echo/summary).
    Later we can allow uploading code, referencing module paths, etc.
    """
    plugin = register_plugin(
        name=req.name,
        description=req.description,
        version=req.version,
        metadata=req.metadata,
        enabled=req.enabled,
    )
    return plugin


@router.get("/plugin/list")
def api_list_plugins():
    return list_plugins()


@router.get("/plugin/{plugin_id}")
def api_get_plugin(plugin_id: str):
    p = get_plugin(plugin_id)
    if p is None:
        raise HTTPException(status_code=404, detail="plugin_not_found")
    return p


@router.delete("/plugin/{plugin_id}")
def api_unregister_plugin(plugin_id: str):
    ok = unregister_plugin(plugin_id)
    if not ok:
        raise HTTPException(status_code=404, detail="plugin_not_found")
    return {"deleted": True}


@router.post("/plugin/{plugin_id}/invoke")
def api_invoke_plugin(plugin_id: str, payload: Dict[str, Any]):
    """
    Invoke a registered plugin with a JSON payload.
    """
    try:
        result = invoke_plugin(plugin_id, payload)
        return {"plugin_id": plugin_id, "result": result}
    except KeyError:
        raise HTTPException(status_code=404, detail="plugin_not_found")
    except Exception as e:
        # Return plugin error as 500 with message
        raise HTTPException(status_code=500, detail=str(e))
