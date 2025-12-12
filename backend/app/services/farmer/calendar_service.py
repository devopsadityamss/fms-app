# backend/app/services/farmer/calendar_service.py

from datetime import datetime, timedelta
from typing import Dict, List, Any


# NOTE:
# This service creates a mock calendar timeline for:
# - crop stages
# - production tasks
# - weather events (later)
# - reminders & important actions
#
# This is a lightweight version to help UI developers build:
# - Calendar View
# - Unit Timeline
# - Stage Progress Bar
# - Weekly Activity Planner
#
# Does NOT use the database yet (as per your instruction).


def generate_stage_timeline(stage_definitions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Generates a mock stage timeline from supplied stage definitions.
    Stage definitions sample:
    [
        { "id": 1, "name": "Sowing", "duration_days": 7 },
        { "id": 2, "name": "Vegetative", "duration_days": 25 },
        ...
    ]
    """

    timeline = []
    start_date = datetime.utcnow()

    for stage in stage_definitions:
        end_date = start_date + timedelta(days=stage.get("duration_days", 5))

        timeline.append({
            "stage_id": stage["id"],
            "stage_name": stage["name"],
            "start_date": start_date,
            "end_date": end_date,
            "duration_days": stage.get("duration_days", 5),
        })

        start_date = end_date  # next stage starts after previous ends

    return timeline


def generate_task_calendar(tasks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Converts tasks into calendar-friendly format.
    Task sample:
    [
        { "id": 1, "name": "Irrigation", "due_days_from_start": 2 },
        { "id": 2, "name": "Fertilization", "due_days_from_start": 10 }
    ]
    """

    calendar = []
    base_date = datetime.utcnow()

    for task in tasks:
        scheduled_date = base_date + timedelta(days=task.get("due_days_from_start", 0))

        calendar.append({
            "task_id": task["id"],
            "task_name": task["name"],
            "scheduled_date": scheduled_date,
            "priority": task.get("priority", "medium"),
            "stage": task.get("stage", "Unknown")
        })

    return calendar


def get_weekly_overview(unit_id: int) -> List[Dict[str, Any]]:
    """
    Generates a mock weekly activity snapshot.
    """

    now = datetime.utcnow()
    return [
        {
            "date": (now + timedelta(days=i)).date(),
            "tasks": [
                {"name": "Irrigation", "priority": "medium"},
                {"name": "Field Check", "priority": "low"},
            ] if i % 2 == 0 else []
        }
        for i in range(7)
    ]


def get_calendar(unit_id: int, stage_definitions: List[Dict[str, Any]], tasks: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    The main unified function: combines stage timeline + task calendar + weekly overview.
    """

    return {
        "unit_id": unit_id,
        "timestamp": datetime.utcnow(),
        "stage_timeline": generate_stage_timeline(stage_definitions),
        "task_calendar": generate_task_calendar(tasks),
        "weekly_overview": get_weekly_overview(unit_id)
    }
