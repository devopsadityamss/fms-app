"""
Labor Compliance Checker Service (stub-ready)
---------------------------------------------

Evaluates whether farm labor practices meet typical agricultural labor norms.

Inputs:
 - Worker attendance data (hours, presence)
 - Worker metadata (optional)
 - Skill/safety certifications (optional)

Checks (Phase-1 stubs):
 - Maximum daily work hours (limit: 8)
 - Maximum weekly work hours (limit: 48)
 - Minimum weekly rest day (1 day/week)
 - Underage worker check (< 18)
 - Safety training requirement (if worker operates machinery)
 - Overtime tracking

Outputs:
 - Per-worker compliance report
 - Overall compliance score (0–100)
 - Violations list
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta, date

# optional imports to integrate with attendance & skill matrix
try:
    from app.services.farmer import worker_attendance_service as attendance_svc
except Exception:
    attendance_svc = None

try:
    from app.services.farmer import skill_matrix_service as skill_svc
except Exception:
    skill_svc = None


# -------------------------------------------------------------
# INTERNAL HELPERS
# -------------------------------------------------------------
def _day_of_week(d: str) -> Optional[int]:
    try:
        return date.fromisoformat(d).weekday()
    except Exception:
        return None


def _sum_hours(records: List[Dict[str, Any]]) -> float:
    return sum(r.get("hours", 0) for r in records if r.get("status") == "present")


def _check_underage(worker_meta: Dict[str, Any]) -> Optional[str]:
    """
    worker_meta may contain:
    {
        "dob": "YYYY-MM-DD",
        "age": <int> (optional),
        "name": ...
    }
    """
    dob = worker_meta.get("dob")
    if dob:
        try:
            born = date.fromisoformat(dob)
            age = (date.today() - born).days // 365
            if age < 18:
                return "Underage worker (<18)"
        except:
            pass

    if worker_meta.get("age") and worker_meta["age"] < 18:
        return "Underage worker (<18)"

    return None


# -------------------------------------------------------------
# MAIN COMPLIANCE CHECK
# -------------------------------------------------------------
def evaluate_worker_compliance(
    worker_id: str,
    month: int,
    year: int,
    worker_meta: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:

    if not attendance_svc:
        return {"error": "attendance_service_unavailable"}

    # 1) Fetch attendance records
    all_records = attendance_svc.list_attendance(worker_id=worker_id)["items"]

    monthly_records = []
    for r in all_records:
        try:
            d = date.fromisoformat(r["date"])
        except:
            continue
        if d.month == month and d.year == year:
            monthly_records.append(r)

    violations = []

    # ---------------------------------------------------------
    # CHECK 1: Underage
    # ---------------------------------------------------------
    if worker_meta:
        v = _check_underage(worker_meta)
        if v:
            violations.append(v)

    # ---------------------------------------------------------
    # CHECK 2: Daily hour limit
    # ---------------------------------------------------------
    for rec in monthly_records:
        if rec.get("hours", 0) > 8:
            violations.append(f"Exceeded daily hour limit on {rec['date']} ({rec['hours']}h)")

    # ---------------------------------------------------------
    # CHECK 3: Weekly hour limit
    # ---------------------------------------------------------
    # Group by week index
    weekly_hours = {}
    for rec in monthly_records:
        try:
            d = date.fromisoformat(rec["date"])
        except:
            continue
        year_week = d.isocalendar()[:2]  # (year, week number)
        weekly_hours.setdefault(year_week, 0)
        weekly_hours[year_week] += rec.get("hours", 0)

    for (y, wk), hrs in weekly_hours.items():
        if hrs > 48:
            violations.append(f"Exceeded weekly hour limit (week {wk}, {hrs}h)")

    # ---------------------------------------------------------
    # CHECK 4: Weekly rest day
    # ---------------------------------------------------------
    # Count days worked per week
    weekly_workdays = {}
    for rec in monthly_records:
        try:
            d = date.fromisoformat(rec["date"])
        except:
            continue
        year_week = d.isocalendar()[:2]
        weekly_workdays.setdefault(year_week, 0)
        if rec["status"] == "present":
            weekly_workdays[year_week] += 1

    for (y, wk), days in weekly_workdays.items():
        if days >= 7:
            violations.append(f"No weekly rest day (week {wk})")

    # ---------------------------------------------------------
    # CHECK 5: Safety certification (if skill matrix available)
    # ---------------------------------------------------------
    if skill_svc:
        skills = skill_svc.list_skills(worker_id)["items"]
        safety_required = any(
            s["skill"] in ["tractor_operation", "sprayer_handling", "machinery_operation"]
            for s in skills
        )
        if safety_required:
            has_safety = any(
                "safety" in (",".join(s.get("certifications", [])).lower())
                for s in skills
            )
            if not has_safety:
                violations.append("Missing safety training certificate")

    # ---------------------------------------------------------
    # COMPLIANCE SCORE
    # ---------------------------------------------------------
    if violations:
        score = max(0, 100 - len(violations) * 8)
    else:
        score = 100

    return {
        "worker_id": worker_id,
        "month": month,
        "year": year,
        "violations": violations,
        "compliance_score": score
    }


# -------------------------------------------------------------
# FARM-WIDE COMPLIANCE SUMMARY
# -------------------------------------------------------------
def farm_compliance_summary(
    worker_ids: List[str],
    month: int,
    year: int
) -> Dict[str, Any]:

    summaries = []
    total_score = 0

    for wid in worker_ids:
        summary = evaluate_worker_compliance(wid, month, year)
        if "error" in summary:
            return summary
        summaries.append(summary)
        total_score += summary["compliance_score"]

    avg_score = round(total_score / len(worker_ids), 2) if worker_ids else 0

    return {
        "month": month,
        "year": year,
        "average_compliance_score": avg_score,
        "worker_summaries": summaries
    }
