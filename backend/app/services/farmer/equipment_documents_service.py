# backend/app/services/farmer/equipment_documents_service.py

from datetime import datetime, timedelta
from threading import Lock
from typing import Dict, Any, Optional, List

# ===========================
#  DOCUMENT STORAGE
# ===========================

_docs_store: Dict[str, List[Dict[str, Any]]] = {}
_docs_lock = Lock()


def add_equipment_document(
    equipment_id: str,
    doc_type: str,
    file_url: str,
    issue_date: Optional[str] = None,
    expiry_date: Optional[str] = None,
    doc_number: Optional[str] = None,
    notes: Optional[str] = None
) -> Dict[str, Any]:
    """
    Adds a document entry for equipment.
    file_url can be local path/S3 URL - currently just stored as string.
    """

    record = {
        "equipment_id": equipment_id,
        "doc_type": doc_type.lower(),
        "file_url": file_url,
        "doc_number": doc_number,
        "issue_date": issue_date,
        "expiry_date": expiry_date,
        "notes": notes,
        "uploaded_at": datetime.utcnow().isoformat()
    }

    with _docs_lock:
        if equipment_id not in _docs_store:
            _docs_store[equipment_id] = []
        _docs_store[equipment_id].append(record)

    return record


def list_equipment_documents(equipment_id: str) -> Dict[str, Any]:
    """Returns all documents belonging to an equipment."""
    with _docs_lock:
        docs = _docs_store.get(equipment_id, [])

    return {
        "equipment_id": equipment_id,
        "count": len(docs),
        "documents": docs
    }


def get_expiring_documents(within_days: int = 30) -> Dict[str, Any]:
    """
    Returns documents expiring within next X days.
    """

    now = datetime.utcnow().date()
    cutoff = now + timedelta(days=within_days)

    results = []

    with _docs_lock:
        for eq_id, docs in _docs_store.items():
            for d in docs:
                expiry = d.get("expiry_date")
                if not expiry:
                    continue

                try:
                    ed = datetime.fromisoformat(expiry).date()
                except:
                    continue

                if now <= ed <= cutoff:
                    results.append({
                        "equipment_id": eq_id,
                        "doc_type": d.get("doc_type"),
                        "doc_number": d.get("doc_number"),
                        "expiry_date": expiry,
                        "days_left": (ed - now).days,
                        "file_url": d.get("file_url"),
                    })

    results.sort(key=lambda x: x["days_left"])

    return {
        "within_days": within_days,
        "count": len(results),
        "expiring_documents": results,
        "checked_at": datetime.utcnow().isoformat()
    }


# ===========================
#  COMPLIANCE INTELLIGENCE
# ===========================

# Mapping of compliance categories → document types
_COMPLIANCE_DOC_TYPES = {
    "insurance": ["insurance", "insurance_certificate"],
    "registration": ["rc", "registration_certificate"],
    "fitness": ["fitness", "fitness_certificate"],
    "emission": ["puc", "pollution", "emission_certificate"]
}


def compute_equipment_compliance(equipment_id: str) -> Optional[Dict[str, Any]]:
    """
    Computes compliance score and alerts for:
    - Insurance
    - RC
    - Fitness Certificate
    - PUC (emission)

    Score = 0–100
    Risk Levels = low / medium / high / critical
    """

    docs_info = list_equipment_documents(equipment_id)
    if docs_info is None:
        return None

    docs = docs_info.get("documents", [])
    now = datetime.utcnow().date()
    alerts = []
    score = 100  # deduct for each problem

    # group documents by compliance category
    grouped_docs = {k: [] for k in _COMPLIANCE_DOC_TYPES.keys()}

    for d in docs:
        dt = d.get("doc_type", "").lower()
        for comp_type, aliases in _COMPLIANCE_DOC_TYPES.items():
            if dt in aliases:
                grouped_docs[comp_type].append(d)

    def parse_expiry(doc):
        expiry = doc.get("expiry_date")
        if not expiry:
            return None, None
        try:
            ed = datetime.fromisoformat(expiry).date()
            return ed, (ed - now).days
        except:
            return None, None

    breakdown = {}

    # evaluate each compliance category
    for comp_type, doc_list in grouped_docs.items():

        # no documents → missing
        if not doc_list:
            alerts.append(f"{comp_type} document missing")
            score -= 25
            breakdown[comp_type] = {"status": "missing"}
            continue

        # use the latest uploaded document
        doc = doc_list[-1]
        exp_date, days_left = parse_expiry(doc)

        if exp_date is None:
            alerts.append(f"{comp_type} document has invalid expiry date")
            score -= 20
            breakdown[comp_type] = {"status": "invalid_date"}
            continue

        if days_left < 0:
            alerts.append(f"{comp_type} is EXPIRED ({abs(days_left)} days ago)")
            score -= 40
            breakdown[comp_type] = {
                "status": "expired",
                "days_left": days_left
            }
        elif days_left <= 7:
            alerts.append(f"{comp_type} expires soon (in {days_left} days)")
            score -= 20
            breakdown[comp_type] = {
                "status": "due_soon",
                "days_left": days_left
            }
        else:
            breakdown[comp_type] = {
                "status": "valid",
                "days_left": days_left
            }

    # clamp score
    score = max(0, min(100, score))

    if score >= 80:
        risk = "low"
    elif score >= 60:
        risk = "medium"
    elif score >= 40:
        risk = "high"
    else:
        risk = "critical"

    return {
        "equipment_id": equipment_id,
        "compliance_score": score,
        "risk_level": risk,
        "alerts": alerts,
        "breakdown": breakdown,
        "evaluated_at": datetime.utcnow().isoformat()
    }


def fleet_compliance_overview() -> Dict[str, Any]:
    """
    Returns compliance summary for ALL equipment with documents.
    """

    results = []

    # We check documents for any equipment_id in docs store
    with _docs_lock:
        eq_ids = list(_docs_store.keys())

    for eid in eq_ids:
        comp = compute_equipment_compliance(eid)
        if comp:
            results.append(comp)

    # sort worst → best
    results.sort(key=lambda x: x["compliance_score"])

    return {
        "count": len(results),
        "fleet_compliance": results,
        "timestamp": datetime.utcnow().isoformat()
    }

from datetime import datetime
from threading import Lock
from typing import Dict, Any, List, Optional

# IMPORTS FROM EQUIPMENT SERVICE
from app.services.farmer.equipment_service import (
    compute_breakdown_probability,
    forecast_equipment_downtime,
    get_warranty_status,
    _equipment_store,      # used only to check if equipment exists
    _store_lock
)

# -----------------------------------------------------------
# Equipment Document Store (in-memory)
# -----------------------------------------------------------

_equipment_documents_store: Dict[str, List[Dict[str, Any]]] = {}
_documents_lock = Lock()

# Required documents per equipment type
REQUIRED_DOCS_BY_TYPE = {
    "tractor": ["rc_book", "insurance", "pollution", "fitness"],
    "harvester": ["rc_book", "insurance", "fitness"],
    "sprayer": ["purchase_invoice"],
    "rotavator": ["purchase_invoice"],
    "power_tiller": ["rc_book", "insurance"],
}


# -----------------------------------------------------------
# CRUD: Add / Update Documents
# -----------------------------------------------------------

def add_equipment_document(
    equipment_id: str,
    document_type: str,
    document_number: Optional[str],
    issue_date: Optional[str],
    expiry_date: Optional[str],
    provider: Optional[str] = None,
    notes: Optional[str] = None,
):
    """
    Save or update a document for an equipment.
    """
    doc = {
        "equipment_id": equipment_id,
        "document_type": document_type.lower(),
        "document_number": document_number,
        "issue_date": issue_date,
        "expiry_date": expiry_date,
        "provider": provider,
        "notes": notes,
        "uploaded_at": datetime.utcnow().isoformat(),
    }

    with _documents_lock:
        existing = _equipment_documents_store.get(equipment_id, [])
        # Replace existing same-type document
        existing = [d for d in existing if d["document_type"] != document_type.lower()]
        existing.append(doc)
        _equipment_documents_store[equipment_id] = existing

    return doc


# -----------------------------------------------------------
# GET ALL DOCUMENTS FOR EQUIPMENT
# -----------------------------------------------------------

def get_documents_for_equipment(equipment_id: str) -> List[Dict[str, Any]]:
    with _documents_lock:
        return _equipment_documents_store.get(equipment_id, [])


# -----------------------------------------------------------
# VERIFY DOCUMENTS (Feature 235 Core Logic)
# -----------------------------------------------------------

def verify_equipment_documents(equipment_id: str) -> Dict[str, Any]:
    """
    Auto-verifies documents:
      - Checks missing required docs
      - Checks expiry (valid / expiring soon / expired)
      - Computes compliance risk score
      - Uses breakdown + downtime + warranty signals to amplify risk
      - Returns recommendations
    """

    # Check equipment exists
    with _store_lock:
        if equipment_id not in _equipment_store:
            return {"equipment_id": equipment_id, "status": "equipment_not_found"}

        eq = _equipment_store[equipment_id]
        eq_type = eq.get("type", "").lower()

    required_docs = REQUIRED_DOCS_BY_TYPE.get(eq_type, [])
    docs = get_documents_for_equipment(equipment_id)

    doc_status_map = {}
    missing_docs = []
    expired_docs = []
    expiring_soon_docs = []

    for req in required_docs:
        matched = [d for d in docs if d["document_type"] == req]

        if not matched:
            missing_docs.append(req)
            continue

        doc = matched[0]
        expiry = doc.get("expiry_date")

        if expiry:
            try:
                exp_date = datetime.fromisoformat(expiry).date()
                days_left = (exp_date - datetime.utcnow().date()).days

                if days_left < 0:
                    doc_status_map[req] = "expired"
                    expired_docs.append(doc)

                elif days_left <= 30:
                    doc_status_map[req] = "expiring_soon"
                    expiring_soon_docs.append(doc)

                else:
                    doc_status_map[req] = "valid"

            except:
                doc_status_map[req] = "invalid_expiry_format"

        else:
            doc_status_map[req] = "no_expiry_provided"

    # ------------------------------
    # Compute Compliance Risk Score
    # ------------------------------

    risk_score = 0
    risk_score += len(missing_docs) * 20
    risk_score += len(expired_docs) * 25
    risk_score += len(expiring_soon_docs) * 10

    # external risk signals
    breakdown = compute_breakdown_probability(equipment_id) or {}
    breakdown_prob = breakdown.get("breakdown_probability", 0)

    downtime = forecast_equipment_downtime(equipment_id, horizon_days=30) or {}
    downtime_days = downtime.get("expected_downtime_days", 0)

    warranty = get_warranty_status(equipment_id) or {}
    warranty_status = warranty.get("status")

    # amplify risk
    if breakdown_prob >= 50:
        risk_score += 10

    if downtime_days >= 3:
        risk_score += 5

    if warranty_status == "expired":
        risk_score += 10

    risk_score = min(100, risk_score)

    # ------------------------------
    # Recommendations
    # ------------------------------

    recommendations = []

    if missing_docs:
        recommendations.append(f"Missing: {', '.join(missing_docs)} — upload required documents.")

    if expired_docs:
        expired_list = [d['document_type'] for d in expired_docs]
        recommendations.append(f"Expired: {', '.join(expired_list)} — renew immediately.")

    if expiring_soon_docs:
        soon_list = [d['document_type'] for d in expiring_soon_docs]
        recommendations.append(f"Expiring soon: {', '.join(soon_list)} — renew within 30 days.")

    if risk_score >= 70:
        recommendations.append("High compliance risk — immediate attention required.")

    if not recommendations:
        recommendations.append("All required documents appear valid and up-to-date.")

    return {
        "equipment_id": equipment_id,
        "equipment_type": eq_type,
        "document_status": doc_status_map,
        "missing_documents": missing_docs,
        "expired_documents": expired_docs,
        "expiring_soon_documents": expiring_soon_docs,
        "risk_score": risk_score,
        "breakdown_probability": breakdown_prob,
        "downtime_days_expected": downtime_days,
        "warranty_status": warranty_status,
        "recommendations": recommendations,
        "verified_at": datetime.utcnow().isoformat(),
    }


# -----------------------------------------------------------
# FLEET-LEVEL VERIFICATION
# -----------------------------------------------------------

def fleet_document_verification() -> Dict[str, Any]:
    results = []

    with _store_lock:
        equipment_ids = list(_equipment_store.keys())

    for eid in equipment_ids:
        results.append(verify_equipment_documents(eid))

    results.sort(key=lambda x: x.get("risk_score", 0), reverse=True)

    return {
        "count": len(results),
        "fleet_document_verification": results,
        "generated_at": datetime.utcnow().isoformat(),
    }
