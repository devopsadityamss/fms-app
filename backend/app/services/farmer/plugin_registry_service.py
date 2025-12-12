# backend/app/services/farmer/plugin_registry_service.py

"""
Simple in-process plugin registry for intelligence modules.

Purpose:
- Allow registering lightweight plugin handlers (callables) at runtime.
- Provide discovery (list / get) and invocation APIs.
- Keep everything in-memory (no DB). Replaceable with a real plugin
  manager later (DB + signed plugins + permissions).

Plugin shape (internal):
{
  "name": str,
  "description": str,
  "version": str,
  "enabled": bool,
  "handler": Callable[[dict], dict],  # invoked with payload -> returns dict
  "metadata": dict
}
"""

from datetime import datetime
from threading import Lock
from typing import Callable, Dict, Any, List, Optional
import uuid

_registry: Dict[str, Dict[str, Any]] = {}
_registry_lock = Lock()


def _now_iso():
    from datetime import datetime
    return datetime.utcnow().isoformat()


def register_plugin(
    name: str,
    description: str = "",
    handler: Optional[Callable[[dict], dict]] = None,
    version: str = "0.1",
    metadata: Optional[Dict[str, Any]] = None,
    enabled: bool = True,
) -> Dict[str, Any]:
    """
    Register a plugin. Handler is a callable(payload) -> dict.
    If handler is None, a default echo-handler is installed.
    Returns plugin record.
    """
    if metadata is None:
        metadata = {}

    if handler is None:
        # default handler returns the payload echoed back
        def _default_handler(payload: dict) -> dict:
            return {"plugin": name, "echo": payload, "note": "default handler"}
        handler = _default_handler

    plugin_id = str(uuid.uuid4())
    plugin = {
        "id": plugin_id,
        "name": name,
        "description": description,
        "version": version,
        "enabled": enabled,
        "handler": handler,
        "metadata": metadata,
        "created_at": _now_iso(),
    }

    with _registry_lock:
        _registry[plugin_id] = plugin

    return sanitize_plugin(plugin)


def sanitize_plugin(plugin: Dict[str, Any]) -> Dict[str, Any]:
    """
    Return a sanitized view of plugin (no handler callable).
    """
    return {
        "id": plugin["id"],
        "name": plugin["name"],
        "description": plugin.get("description"),
        "version": plugin.get("version"),
        "enabled": plugin.get("enabled"),
        "metadata": plugin.get("metadata"),
        "created_at": plugin.get("created_at"),
    }


def list_plugins() -> List[Dict[str, Any]]:
    with _registry_lock:
        return [sanitize_plugin(p) for p in _registry.values()]


def get_plugin(plugin_id: str) -> Optional[Dict[str, Any]]:
    with _registry_lock:
        plugin = _registry.get(plugin_id)
        if not plugin:
            return None
        return sanitize_plugin(plugin)


def unregister_plugin(plugin_id: str) -> bool:
    with _registry_lock:
        if plugin_id in _registry:
            del _registry[plugin_id]
            return True
        return False


def invoke_plugin(plugin_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Invoke the plugin's handler with the provided payload.
    Returns the handler response as dict.
    Will raise KeyError if plugin not found, or re-raise plugin exceptions.
    """
    with _registry_lock:
        plugin = _registry.get(plugin_id)
        if not plugin:
            raise KeyError(f"Plugin not found: {plugin_id}")
        if not plugin.get("enabled", True):
            return {"error": "plugin_disabled", "plugin_id": plugin_id}

        handler = plugin.get("handler")

    # Call handler outside lock
    result = handler(payload if payload is not None else {})
    if not isinstance(result, dict):
        # normalize
        return {"result": result}
    return result


# -----------------------------------------
# Register a small built-in example plugin
# -----------------------------------------
def _builtin_summary_plugin(payload: dict) -> dict:
    """
    Example plugin: returns brief summary of the payload (counts keys).
    """
    keys = list(payload.keys()) if isinstance(payload, dict) else []
    return {
        "summary": {"key_count": len(keys), "keys": keys},
        "note": "builtin summary"
    }


# register builtin (id will be generated)
_builtin = register_plugin(
    name="builtin-summary",
    description="Returns a small summary of payload keys",
    handler=_builtin_summary_plugin,
    version="0.1",
    metadata={"type": "utility"},
    enabled=True,
)
