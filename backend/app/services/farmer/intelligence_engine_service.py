# backend/app/services/farmer/intelligence_engine_service.py

from datetime import datetime
from typing import Dict, Any

from app.services.farmer.weather_service import get_current_weather
from app.services.farmer.advisory_service import get_all_advisory
from app.services.farmer.alert_service import get_all_alerts
from app.services.farmer.calendar_service import get_calendar
from app.services.farmer.health_service import get_crop_health_score
from app.services.farmer.prediction_service import get_all_predictions
from app.services.farmer.inventory_service import get_inventory_plan
from app.services.farmer.cost_service import get_cost_analysis
from app.services.farmer.notification_service import get_all_notifications
from app.services.farmer.soil_service import get_soil_intelligence
from app.services.farmer.pest_service import get_pest_intel
from app.services.farmer.sustainability_service import get_sustainability_summary
from app.services.farmer.profitability_service import get_profitability_summary
from app.services.farmer.market_service import get_market_intelligence

from app.services.farmer.plugin_registry_service import list_plugins, invoke_plugin

# Unified intelligence engine that aggregates primary modules (mock, no DB)
def get_full_intelligence(unit_id: int, stage: str, current_stock: dict = None, crop: str = "generic", days_since_application: int = 0, material_name: str = "") -> Dict[str, Any]:
    """
    Combines multiple services into a single intelligence payload.
    This is intended as the one-stop API for the frontend dashboard.
    """
    # Core building blocks
    weather = get_current_weather(unit_id)
    soil = get_soil_intelligence(unit_id, crop)
    advisory = get_all_advisory(unit_id, stage, weather)
    alerts = get_all_alerts(unit_id, stage, weather, overdue_tasks=0)
    calendar = get_calendar(unit_id, [], [])  # frontend will replace with real stage/tasks later
    health = get_crop_health_score(unit_id, stage, weather)
    preds = get_all_predictions(stage, health["score"], weather)
    inventory = get_inventory_plan(unit_id, stage, current_stock or {})
    cost = get_cost_analysis(unit_id, stage, actual_cost_spent=0)
    notifications = get_all_notifications(unit_id, weather, health["score"], overdue_tasks=0, upcoming_tasks=0, pest_alerts_count=len(alerts["alerts"]), stage_name=stage)
    pest = get_pest_intel(unit_id, stage, weather)
    sustainability = get_sustainability_summary(unit_id)
    market = get_market_intelligence(unit_id, crop)
    profitability = get_profitability_summary(unit_id, preds.get("yield_prediction", {}), cost.get("season_projection", {}), market_price_per_kg=1.0)

    return {
        "unit_id": unit_id,
        "timestamp": datetime.utcnow(),
        "weather": weather,
        "soil": soil,
        "advisory": advisory,
        "alerts": alerts,
        "calendar": calendar,
        "health": health,
        "predictions": preds,
        "inventory": inventory,
        "cost": cost,
        "notifications": notifications,
        "pest": pest,
        "sustainability": sustainability,
        "market": market,
        "profitability": profitability,
    }

def get_full_intelligence(unit_id: int, stage: str, current_stock: dict = None, crop: str = "generic",
                          days_since_application: int = 0, material_name: str = "") -> Dict[str, Any]:

    # Core building blocks
    weather = get_current_weather(unit_id)
    soil = get_soil_intelligence(unit_id, crop)
    advisory = get_all_advisory(unit_id, stage, weather)
    alerts = get_all_alerts(unit_id, stage, weather, overdue_tasks=0)
    calendar = get_calendar(unit_id, [], [])
    health = get_crop_health_score(unit_id, stage, weather)
    preds = get_all_predictions(stage, health["score"], weather)
    inventory = get_inventory_plan(unit_id, stage, current_stock or {})
    cost = get_cost_analysis(unit_id, stage, actual_cost_spent=0)
    notifications = get_all_notifications(unit_id, weather, health["score"], overdue_tasks=0,
                                          upcoming_tasks=0, pest_alerts_count=len(alerts["alerts"]), stage_name=stage)
    pest = get_pest_intel(unit_id, stage, weather)
    sustainability = get_sustainability_summary(unit_id)
    market = get_market_intelligence(unit_id, crop)
    profitability = get_profitability_summary(unit_id, preds.get("yield_prediction", {}),
                                              cost.get("season_projection", {}), market_price_per_kg=1.0)

    # --- PLUGIN EXECUTION ENGINE ---
    plugin_results = {}
    for plugin in list_plugins():
        plugin_id = plugin["id"]
        try:
            result = invoke_plugin(plugin_id, {
                "unit_id": unit_id,
                "stage": stage,
                "crop": crop,
                "weather": weather,
                "soil": soil,
                "health": health,
                "alerts": alerts,
                "predictions": preds,
                "inventory": inventory,
                "cost": cost,
                "market": market,
                "pest": pest
            })
            plugin_results[plugin_id] = {"success": True, "output": result}
        except Exception as e:
            plugin_results[plugin_id] = {"success": False, "error": str(e)}

    # --- UNIFIED INTELLIGENCE PAYLOAD ---
    return {
        "unit_id": unit_id,
        "timestamp": datetime.utcnow(),
        "weather": weather,
        "soil": soil,
        "advisory": advisory,
        "alerts": alerts,
        "calendar": calendar,
        "health": health,
        "predictions": preds,
        "inventory": inventory,
        "cost": cost,
        "notifications": notifications,
        "pest": pest,
        "sustainability": sustainability,
        "market": market,
        "profitability": profitability,

        # ---- NEW SECTION ----
        "plugins": plugin_results
    }