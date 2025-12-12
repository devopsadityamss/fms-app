# backend/app/api/farmer/calendar.py

from fastapi import APIRouter
from typing import List, Dict, Any
from app.services.farmer.calendar_service import (
    generate_stage_timeline,
    generate_task_calendar,
    get_weekly_overview,
    get_calendar,
)

router = APIRouter()


@router.get("/calendar/{unit_id}")
def calendar_overview(
    unit_id: int,
    stage_definitions: List[Dict[str, Any]] = None,
    tasks: List[Dict[str, Any]] = None
):
    """
    Returns complete calendar data:
    - Stage timeline (Gantt style)
    - Task calendar (scheduled tasks)
    - Weekly overview (daily tasks)

    Frontend will pass mock stage definitions & tasks until DB is ready.
    """

    # Default mock stage definitions
    if stage_definitions is None:
        stage_definitions = [
            {"id": 1, "name": "Sowing", "duration_days": 7},
            {"id": 2, "name": "Vegetative", "duration_days": 25},
            {"id": 3, "name": "Flowering", "duration_days": 20},
            {"id": 4, "name": "Fruiting", "duration_days": 15},
        ]

    # Default mock tasks
    if tasks is None:
        tasks = [
            {"id": 1, "name": "Irrigation", "due_days_from_start": 3},
            {"id": 2, "name": "Fertilizer Application", "due_days_from_start": 10},
        ]

    return get_calendar(unit_id, stage_definitions, tasks)


@router.get("/calendar/{unit_id}/timeline")
def calendar_stage_timeline(unit_id: int):
    """
    Returns only stage timeline.
    """

    mock_stage_definitions = [
        {"id": 1, "name": "Sowing", "duration_days": 7},
        {"id": 2, "name": "Vegetative", "duration_days": 25},
        {"id": 3, "name": "Flowering", "duration_days": 20},
        {"id": 4, "name": "Fruiting", "duration_days": 15},
    ]

    return generate_stage_timeline(mock_stage_definitions)


@router.get("/calendar/{unit_id}/tasks")
def calendar_task_schedule(unit_id: int):
    """
    Returns only task calendar.
    """

    mock_tasks = [
        {"id": 1, "name": "Irrigation", "due_days_from_start": 3},
        {"id": 2, "name": "Spraying", "due_days_from_start": 7},
        {"id": 3, "name": "Weeding", "due_days_from_start": 12},
    ]

    return generate_task_calendar(mock_tasks)


@router.get("/calendar/{unit_id}/weekly")
def calendar_weekly(unit_id: int):
    """
    Returns weekly overview.
    """

    return get_weekly_overview(unit_id)
