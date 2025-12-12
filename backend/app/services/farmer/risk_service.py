# backend/app/services/farmer/risk_service.py

"""
Combined Risk Assessment Engine

This module generates:
- weather risk score
- pest/disease risk score
- health-based risk
- irrigation/water scarcity risk
- cost overrun risk
- market volatility risk
- unified weighted risk score (0–100)
- actionable recommendations

No DB required. Fully mock logic for now.
"""

from datetime import datetime
from typing import Dict, Any


def calculate_weather_risk(weather: Dict[str, Any]) -> Dict[str, Any]:
    temp = weather.get("temperature", 28)
    wind = weather.get("wind_speed", 5)
    humidity = weather.get("humidity", 60)
    rain_chance = weather.get("rain_chance", 20)

    score = 0

    if temp > 35:
        score += 25
    elif temp > 30:
        score += 15

    if wind > 20:
        score += 20
    elif wind > 12:
        score += 10

    if rain_chance > 60:
        score += 20
    elif rain_chance > 30:
        score += 10

    return {
        "score": min(score, 100),
        "details": {
            "temperature": temp,
            "wind_speed": wind,
            "humidity": humidity,
            "rain_chance": rain_chance
        }
    }


def calculate_pest_risk(pest_intel: Dict[str, Any]) -> Dict[str, Any]:
    count = pest_intel.get("summary_count", 0)
    score = min(100, count * 20)  # simple multiplier
    return {"score": score, "risk_items": pest_intel.get("risks", [])}


def calculate_health_risk(health: Dict[str, Any]) -> Dict[str, Any]:
    health_score = health.get("score", 80)
    score = max(0, 100 - health_score)  # low health = high risk
    return {"score": score, "health_score": health_score}


def calculate_irrigation_risk(soil: Dict[str, Any]) -> Dict[str, Any]:
    moisture = soil.get("soil_snapshot", {}).get("moisture_percent", 30)
    if moisture < 15:
        score = 60
    elif moisture < 25:
        score = 30
    else:
        score = 10
    return {"score": score, "moisture": moisture}


def calculate_cost_risk(cost: Dict[str, Any]) -> Dict[str, Any]:
    analysis = cost.get("overrun_analysis", {})
    risk = analysis.get("overrun_percent", 0)
    return {"score": min(100, max(0, int(risk))), "overrun_details": analysis}


def calculate_market_risk(market: Dict[str, Any]) -> Dict[str, Any]:
    trend = market.get("market_trend", {}).get("trend", "stable")
    if trend == "falling":
        score = 40
    elif trend == "rising":
        score = 10
    else:
        score = 20
    return {"score": score, "trend": trend}


def compute_unified_risk(
    unit_id: int,
    weather: Dict[str, Any],
    pest_intel: Dict[str, Any],
    health: Dict[str, Any],
    soil: Dict[str, Any],
    cost: Dict[str, Any],
    market: Dict[str, Any],
) -> Dict[str, Any]:

    weather_risk = calculate_weather_risk(weather)
    pest_risk = calculate_pest_risk(pest_intel)
    health_risk = calculate_health_risk(health)
    irrigation_risk = calculate_irrigation_risk(soil)
    cost_risk = calculate_cost_risk(cost)
    market_risk = calculate_market_risk(market)

    # Weighted unified score
    total = (
        weather_risk["score"] * 0.25 +
        pest_risk["score"] * 0.20 +
        health_risk["score"] * 0.20 +
        irrigation_risk["score"] * 0.15 +
        cost_risk["score"] * 0.10 +
        market_risk["score"] * 0.10
    )
    unified = min(100, int(total))

    recommendations = []
    if unified > 70:
        recommendations.append("High overall risk: immediate inspection required.")
    if pest_risk["score"] > 40:
        recommendations.append("High pest/disease risk: spray or scouting recommended.")
    if irrigation_risk["score"] > 30:
        recommendations.append("Low soil moisture: schedule irrigation soon.")
    if weather_risk["score"] > 40:
        recommendations.append("Weather risk high: protect crop from heat/wind/rain.")
    if cost_risk["score"] > 20:
        recommendations.append("Cost overrun likely: review usage of fertilizers/chemicals.")
    if market_risk["trend"] == "falling":
        recommendations.append("Market prices falling: delay selling if possible.")

    return {
        "unit_id": unit_id,
        "timestamp": datetime.utcnow(),
        "unified_score": unified,
        "breakdown": {
            "weather": weather_risk,
            "pest": pest_risk,
            "health": health_risk,
            "irrigation": irrigation_risk,
            "cost": cost_risk,
            "market": market_risk,
        },
        "recommendations": recommendations,
    }
