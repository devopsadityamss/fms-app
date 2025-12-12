# backend/app/services/farmer/market_service.py

from datetime import datetime, timedelta
from typing import Dict, Any, List

# Mock market intelligence: price trends, best sell window.

def get_mock_price_series(crop: str = "generic", days: int = 14) -> List[Dict[str, Any]]:
    """Generate a mock price timeseries for 'days' days."""
    base_price = 100  # arbitrary
    series = []
    for i in range(days):
        series.append({
            "date": (datetime.utcnow() - timedelta(days=(days - i))).date(),
            "price_per_quintal": base_price + (i % 5) * 2  # simple wave
        })
    return series


def get_market_trend(crop: str = "generic") -> Dict[str, Any]:
    """Return a high-level market trend."""
    series = get_mock_price_series(crop, days=14)
    recent = series[-5:]
    avg_recent = sum(item["price_per_quintal"] for item in recent) / len(recent)
    avg_all = sum(item["price_per_quintal"] for item in series) / len(series)
    trend = "rising" if avg_recent > avg_all else "falling" if avg_recent < avg_all else "stable"
    return {
        "crop": crop,
        "trend": trend,
        "recent_average": avg_recent,
        "series": series
    }


def suggest_best_sell_window(crop: str = "generic") -> Dict[str, Any]:
    """Mock suggestion for best time to sell."""
    return {
        "crop": crop,
        "suggestion": "Wait for price peak in 2-3 weeks" if crop != "generic" else "Monitor weekly trend",
        "confidence": "low" if crop == "generic" else "medium"
    }


def get_market_intelligence(unit_id: int, crop: str = "generic") -> Dict[str, Any]:
    return {
        "unit_id": unit_id,
        "timestamp": datetime.utcnow(),
        "market_trend": get_market_trend(crop),
        "sell_window": suggest_best_sell_window(crop),
    }
