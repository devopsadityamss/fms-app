# backend/app/services/farmer/season_calendar_service.py

from datetime import datetime, timedelta, date
from threading import Lock
from typing import Dict, Any, List, Optional
import csv
import io

# reuse stores
from app.services.farmer.unit_service import _unit_store
from app.services.farmer.stage_service import _stage_template_store
from app.services.farmer.task_service import _task_templates_store

# in-memory calendar store
_calendar_store: Dict[str, Dict[str, Any]] = {}  # unit_id -> calendar dict
_calendar_lock = Lock()

# defaults
DEFAULT_STAGE_GAP_DAYS = 2   # gap between stages
DEFAULT_WORKING_DAYS_PER_WEEK = 6  # farmer works 6 days by default


def _parse_date(d: Optional[str]) -> Optional[date]:
    if not d:
        return None
    try:
        return datetime.fromisoformat(d).date()
    except Exception:
        try:
            return datetime.strptime(d, "%Y-%m-%d").date()
        except Exception:
            return None


def _add_working_days(start: date, days: int, working_days_per_week: int = DEFAULT_WORKING_DAYS_PER_WEEK) -> date:
    # naive: skip Sundays if working_days_per_week == 6; otherwise treat all days as working
    if working_days_per_week >= 7:
        return start + timedelta(days=days)
    cur = start
    added = 0
    while added < days:
        cur = cur + timedelta(days=1)
        # assume Sunday is non-working when 6 days/week
        if working_days_per_week == 6 and cur.weekday() == 6:
            continue
        added += 1
    return cur


def _format_iso(d: date) -> str:
    return d.isoformat()


def generate_season_calendar_for_unit(
    unit_id: str,
    season_start_date_iso: Optional[str] = None,
    use_working_days_per_week: int = DEFAULT_WORKING_DAYS_PER_WEEK,
    skip_rainy_windows: Optional[List[Dict[str, str]]] = None,
    stage_gap_days: int = DEFAULT_STAGE_GAP_DAYS
) -> Optional[Dict[str, Any]]:
    """
    Generate a season calendar for a production unit.
    - season_start_date_iso: override planting/sowing start date (ISO string 'YYYY-MM-DD'), else uses unit.planned_start or today.
    - use_working_days_per_week: 7 or 6 (skip Sundays)
    - skip_rainy_windows: optional list of {"start":"YYYY-MM-DD","end":"YYYY-MM-DD"} where operations should be avoided; tasks inside are shifted forward
    - stage_gap_days: days to leave between stages
    Returns calendar dict (also stored in-memory).
    """
    unit = _unit_store.get(unit_id)
    if not unit:
        return None

    # get stage template
    template_id = unit.get("stage_template_id")
    template = _stage_template_store.get(template_id) or {}
    stages = template.get("stages", [])

    # determine season start
    start_date = _parse_date(season_start_date_iso) or _parse_date(unit.get("planned_start")) or datetime.utcnow().date()

    # normalize skip windows
    skip_windows = []
    if skip_rainy_windows:
        for w in skip_rainy_windows:
            s = _parse_date(w.get("start"))
            e = _parse_date(w.get("end"))
            if s and e and e >= s:
                skip_windows.append({"start": s, "end": e})

    calendar_entries: List[Dict[str, Any]] = []
    cursor_date = start_date

    for stage_idx, stage in enumerate(stages):
        stage_name = stage.get("name", f"stage_{stage_idx}")
        # stage_duration_days can be specified in stage metadata; default to 14
        duration = int(stage.get("duration_days", 14) or 14)
        stage_start = cursor_date
        stage_end = _add_working_days(stage_start, duration - 1, use_working_days_per_week)

        # schedule tasks inside stage
        ops = stage.get("operations", [])
        # if operations carry 'offset_days' in task template, respect that; else distribute evenly
        if ops:
            # compute offsets if not present: evenly spaced
            n = len(ops)
            for i, op_id in enumerate(ops):
                task_def = _task_templates_store.get(op_id, {})
                # use task offset if exists
                op_offset = task_def.get("offset_days")
                if op_offset is None:
                    # distribute
                    op_offset = int((i / max(1, n - 1)) * (duration - 1)) if n > 1 else 0
                # due/date calculation
                scheduled_start = _add_working_days(stage_start, int(op_offset), use_working_days_per_week)
                # estimated duration (task-level) default 1 day or provided
                est_days = int(task_def.get("estimated_days", 1) or 1)
                scheduled_end = _add_working_days(scheduled_start, max(0, est_days - 1), use_working_days_per_week)

                # Shift forward if falls in skip window
                for w in skip_windows:
                    if scheduled_start >= w["start"] and scheduled_start <= w["end"]:
                        # move to day after window end
                        scheduled_start = _add_working_days(w["end"], 1, use_working_days_per_week)
                        scheduled_end = _add_working_days(scheduled_start, max(0, est_days - 1), use_working_days_per_week)

                entry = {
                    "unit_id": unit_id,
                    "stage_index": stage_idx,
                    "stage_name": stage_name,
                    "task_id": op_id,
                    "task_name": task_def.get("name"),
                    "task_type": task_def.get("type"),
                    "scheduled_start_iso": _format_iso(scheduled_start),
                    "scheduled_end_iso": _format_iso(scheduled_end),
                    "estimated_days": est_days,
                    "notes": task_def.get("notes", "")
                }
                calendar_entries.append(entry)

        # move cursor to end + gap
        cursor_date = _add_working_days(stage_end, stage_gap_days, use_working_days_per_week)

    calendar = {
        "unit_id": unit_id,
        "unit_name": unit.get("name"),
        "crop": unit.get("crop"),
        "season_start_date_iso": _format_iso(start_date),
        "generated_at": datetime.utcnow().isoformat(),
        "entries": calendar_entries
    }

    with _calendar_lock:
        _calendar_store[unit_id] = calendar

    return calendar


def get_calendar_for_unit(unit_id: str) -> Optional[Dict[str, Any]]:
    with _calendar_lock:
        return _calendar_store.get(unit_id)


def list_all_calendars() -> Dict[str, Any]:
    with _calendar_lock:
        items = list(_calendar_store.values())
    return {"count": len(items), "calendars": items}


def regenerate_calendar(unit_id: str, **kwargs) -> Optional[Dict[str, Any]]:
    # convenience wrapper: re-run generation with kwargs (e.g., new start date)
    return generate_season_calendar_for_unit(unit_id, **kwargs)


def export_calendar_csv(unit_id: str) -> Optional[str]:
    """
    Export stored calendar to CSV (string). Columns: unit,stage,task,start,end,est_days,task_type,notes
    """
    cal = get_calendar_for_unit(unit_id)
    if not cal:
        return None

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["unit_id", "unit_name", "crop", "stage_index", "stage_name", "task_id", "task_name", "task_type", "scheduled_start_iso", "scheduled_end_iso", "estimated_days", "notes"])

    for e in cal.get("entries", []):
        writer.writerow([
            cal.get("unit_id"),
            cal.get("unit_name"),
            cal.get("crop"),
            e.get("stage_index"),
            e.get("stage_name"),
            e.get("task_id"),
            e.get("task_name"),
            e.get("task_type"),
            e.get("scheduled_start_iso"),
            e.get("scheduled_end_iso"),
            e.get("estimated_days"),
            e.get("notes")
        ])

    return output.getvalue()
