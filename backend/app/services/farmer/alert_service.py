# backend/app/services/farmer/alert_service.py

from datetime import datetime
from typing import List, Dict, Any


# NOTE:
# This file generates mock alerts for:
# - weather risks
# - disease & pest risks
# - missed tasks
# - growth anomalies
# Later these will integrate with:
# - weather_service
# - prediction_service
# - disease ML models
# - task completion logs
# Currently: hard-coded patterns to support UI/API development.


def get_weather_alerts(unit_id: int, weather: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Generates alerts based on mock weather response.
    """

    alerts = []

    if weather.get("temperature", 0) > 35:
        alerts.append({
            "type": "weather",
            "severity": "high",
            "title": "Heat Stress Risk",
            "message": "Temperature is high — irrigate crops during cooler hours.",
            "timestamp": datetime.utcnow(),
        })

    if weather.get("rainfall_mm", 0) > 20:
        alerts.append({
            "type": "weather",
            "severity": "medium",
            "title": "Heavy Rainfall Warning",
            "message": "Avoid fertilizing or spraying during rainfall.",
            "timestamp": datetime.utcnow(),
        })

    if weather.get("humidity", 0) > 80:
        alerts.append({
            "type": "weather",
            "severity": "low",
            "title": "High Humidity Alert",
            "message": "Monitor crops for fungal infections.",
            "timestamp": datetime.utcnow(),
        })

    return alerts


def get_disease_and_pest_alerts(unit_id: int, stage_name: str) -> List[Dict[str, Any]]:
    """
    Mock rules for pest/disease alerts by stage.
    """

    alerts = []

    stage_name = stage_name.lower()

    if stage_name in ["vegetative", "flowering"]:
        alerts.append({
            "type": "pest",
            "severity": "medium",
            "title": "Leaf Miner Risk",
            "message": "Monitor lower leaves for mining patterns; apply neem oil if needed.",
            "timestamp": datetime.utcnow(),
        })

    if stage_name == "flowering":
        alerts.append({
            "type": "disease",
            "severity": "high",
            "title": "Blight Susceptibility",
            "message": "High susceptibility to early blight — inspect plants daily.",
            "timestamp": datetime.utcnow(),
        })

    return alerts


def get_task_alerts(unit_id: int, overdue_tasks_count: int) -> List[Dict[str, Any]]:
    """
    Alerts for overdue or upcoming tasks.
    Later will integrate with task_service.
    """

    alerts = []

    if overdue_tasks_count > 0:
        alerts.append({
            "type": "task",
            "severity": "high",
            "title": "Overdue Tasks",
            "message": f"{overdue_tasks_count} tasks are overdue. Please complete them soon.",
            "timestamp": datetime.utcnow(),
        })

    return alerts


def get_growth_anomaly_alerts(unit_id: int) -> List[Dict[str, Any]]:
    """
    Placeholder for growth anomaly detection.
    Future: integrate with prediction_service and crop health engines.
    """

    # Mock pattern
    anomaly_detected = False

    if anomaly_detected:
        return [{
            "type": "growth",
            "severity": "medium",
            "title": "Growth Pattern Anomaly",
            "message": "Growth is below expected rate — check irrigation and nutrient levels.",
            "timestamp": datetime.utcnow(),
        }]

    return []


def get_all_alerts(unit_id: int, stage_name: str, weather: Dict[str, Any], overdue_tasks: int = 0):
    """
    Combines ALL alert categories into one structured response.
    """

    weather_alerts = get_weather_alerts(unit_id, weather)
    pest_disease_alerts = get_disease_and_pest_alerts(unit_id, stage_name)
    task_alerts = get_task_alerts(unit_id, overdue_tasks)
    anomaly_alerts = get_growth_anomaly_alerts(unit_id)

    return {
        "unit_id": unit_id,
        "timestamp": datetime.utcnow(),
        "alerts": weather_alerts + pest_disease_alerts + task_alerts + anomaly_alerts
    }
