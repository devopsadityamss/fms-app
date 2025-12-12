"""
Document Manager Service (stub-ready)
-------------------------------------

Stores metadata about uploaded documents for the farmer POV.

Each document includes:
 - id
 - name
 - type/category: invoice | soil_report | id_proof | contract | misc
 - tags: list[str]
 - unit_id: optional
 - uploaded_at
 - notes
 - file_metadata: size, content_type, (optional) filename
 - file_content: optional raw bytes (NOT recommended for production)
"""

from typing import Dict, Any, Optional, List
from datetime import datetime
import uuid


# ---------------------------------------------------------------------
# In-memory storage
# ---------------------------------------------------------------------
_doc_store: Dict[str, Dict[str, Any]] = {}


def _new_id() -> str:
    return str(uuid.uuid4())


def _now() -> str:
    return datetime.utcnow().isoformat()


# ---------------------------------------------------------------------
# Create
# ---------------------------------------------------------------------
def create_document(
    name: str,
    doc_type: str,
    tags: Optional[List[str]],
    unit_id: Optional[str],
    file_bytes: Optional[bytes],
    content_type: Optional[str],
    notes: Optional[str],
) -> Dict[str, Any]:

    doc_id = _new_id()

    record = {
        "id": doc_id,
        "name": name,
        "doc_type": doc_type,
        "tags": tags or [],
        "unit_id": unit_id,
        "notes": notes,
        "uploaded_at": _now(),
        "file_metadata": {
            "content_type": content_type,
            "size": len(file_bytes) if file_bytes else 0,
        },
        # In production: DO NOT store file bytes in memory.
        # Replace with S3/GCS URL or database reference.
        "file_content": file_bytes,
    }

    _doc_store[doc_id] = record
    return record


# ---------------------------------------------------------------------
# Read
# ---------------------------------------------------------------------
def get_document(doc_id: str) -> Optional[Dict[str, Any]]:
    return _doc_store.get(doc_id)


# ---------------------------------------------------------------------
# List / Filter
# ---------------------------------------------------------------------
def list_documents(
    doc_type: Optional[str] = None,
    unit_id: Optional[str] = None,
    tag: Optional[str] = None
) -> Dict[str, Any]:

    items = list(_doc_store.values())

    if doc_type:
        items = [i for i in items if i.get("doc_type") == doc_type]

    if unit_id:
        items = [i for i in items if i.get("unit_id") == unit_id]

    if tag:
        items = [i for i in items if tag in i.get("tags", [])]

    return {"count": len(items), "items": items}


# ---------------------------------------------------------------------
# Delete
# ---------------------------------------------------------------------
def delete_document(doc_id: str) -> bool:
    if doc_id in _doc_store:
        del _doc_store[doc_id]
        return True
    return False


# ---------------------------------------------------------------------
# Reset (for tests)
# ---------------------------------------------------------------------
def _clear_store():
    _doc_store.clear()
