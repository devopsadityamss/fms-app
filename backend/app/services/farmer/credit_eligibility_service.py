# backend/app/services/farmer/credit_eligibility_service.py

from datetime import datetime, timedelta
from threading import Lock
from typing import Dict, Any, Optional, List
import math

# Reuse earlier services (best-effort imports, fallbacks applied)
try:
    from app.services.farmer.financial_ledger_service import compute_cashflow_summary, list_entries
except Exception:
    compute_cashflow_summary = None
    list_entries = None

try:
    from app.services.farmer.profitability_service import compute_profitability
except Exception:
    compute_profitability = None

try:
    from app.services.farmer.yield_forecasting_service import forecast_yield_for_unit
except Exception:
    forecast_yield_for_unit = None

try:
    from app.services.farmer.risk_alerts_service import list_alerts
except Exception:
    list_alerts = None

# equipment store as collateral proxy (best-effort)
try:
    from app.services.farmer.equipment_service import _equipment_store
except Exception:
    _equipment_store = {}

_credit_app_store: Dict[str, Dict[str, Any]] = {}
_credit_lock = Lock()

# default weights for scoring components (sum to 1.0)
DEFAULT_WEIGHTS = {
    "cashflow_stability": 0.30,
    "repayment_capacity": 0.25,
    "yield_stability": 0.15,
    "risk_profile": 0.15,
    "collateral": 0.10
}


def _safe_float(v, d=0.0):
    try:
        return float(v)
    except Exception:
        return d


def _compute_cashflow_score(farmer_id: Optional[str], lookback_days: int = 180) -> Dict[str, Any]:
    """
    Compute cashflow stability score (0-100) using ledger summary:
    - low volatility & positive net -> high score
    - heavy negative net or erratic -> low score
    """
    if compute_cashflow_summary is None or list_entries is None:
        return {"score": 60, "reason": "ledger_module_missing"}

    # compute last 6 months window
    end = datetime.utcnow().date()
    start = end - timedelta(days=lookback_days)
    sd = start.isoformat()
    ed = end.isoformat()

    s = compute_cashflow_summary(unit_id=None, start_date=sd, end_date=ed)
    total_income = _safe_float(s.get("total_income", 0))
    total_expense = _safe_float(s.get("total_expense", 0))
    net = total_income - total_expense

    # volatility: compute variance across monthly expense in period (if available)
    monthly = s.get("monthly_expense", {}) or {}
    vals = list(monthly.values())
    if len(vals) >= 2:
        mean = sum(vals) / len(vals)
        var = sum((x - mean) ** 2 for x in vals) / len(vals)
        std = math.sqrt(var)
    else:
        std = 0.0

    # heuristics
    if total_income <= 0 and net <= 0:
        score = 20
        reason = "no_positive_income_recently"
    else:
        # base on net / income ratio and low volatility
        profit_margin = (net / total_income) if total_income > 0 else -1
        margin_score = max(0, min(1.0, (profit_margin + 0.5)))  # normalize roughly
        vol_penalty = max(0.0, min(1.0, std / max(1.0, mean if vals else 100.0)))
        score = int(round((0.7 * margin_score + 0.3 * (1 - vol_penalty)) * 100))
        reason = f"net={round(net,2)},std={round(std,2)}"

    return {"score": max(0, min(100, int(score))), "details": {"total_income": total_income, "total_expense": total_expense, "net": net, "std_monthly_expense": round(std,2)}, "reason": reason}


def _compute_repayment_capacity(unit_id: Optional[str], market_price_per_quintal: Optional[float] = None) -> Dict[str, Any]:
    """
    Uses profitability model to estimate annual net cash available for debt service.
    Returns a score and an estimated recommended loan amount (very conservative).
    """
    if compute_profitability is None:
        return {"score": 60, "annual_surplus_estimate": 0.0, "reason": "profitability_module_missing"}

    # If unit_id provided, compute for that unit; else aggregate across units via rough approach
    try:
        # call profitability with market_price if available; otherwise pass 0 to avoid revenue calc
        pf = compute_profitability(unit_id or "", market_price_per_quintal or 0.0)
        expected_profit = _safe_float(pf.get("profit_forecast", {}).get("expected_profit", 0.0))
        # annualize: assuming similar per season and 1-2 seasons/year; conservatively multiply by 1.2
        annual_surplus = expected_profit * 1.2
        if annual_surplus <= 0:
            score = 30
        else:
            # map surplus to score: 0->30, small->50, healthy->90
            if annual_surplus < 10000:
                score = 50
            elif annual_surplus < 50000:
                score = 70
            else:
                score = 90
        return {"score": score, "annual_surplus_estimate": round(annual_surplus,2), "reason": f"expected_profit={expected_profit}"}
    except Exception as e:
        return {"score": 55, "annual_surplus_estimate": 0.0, "reason": f"error:{str(e)}"}


def _compute_yield_stability_score(unit_id: Optional[str]) -> Dict[str, Any]:
    """
    Uses yield forecast confidence if available to compute a 0-100 stability score.
    """
    if forecast_yield_for_unit is None:
        return {"score": 65, "reason": "yield_module_missing"}

    try:
        if not unit_id:
            # fallback neutral
            return {"score": 65, "reason": "no_unit_provided"}
        y = forecast_yield_for_unit(unit_id)
        conf = _safe_float(y.get("confidence_score", 60))
        # normalize to 0-100 (confidence already 0-100)
        score = int(max(0, min(100, conf)))
        return {"score": score, "details": {"expected_yield_quintal": y.get("expected_yield_quintal")}, "reason": f"conf={conf}"}
    except Exception as e:
        return {"score": 60, "reason": f"error:{str(e)}"}


def _compute_risk_profile_score(farmer_id: Optional[str], unit_id: Optional[str]) -> Dict[str, Any]:
    """
    Use risk alerts: more open high severity alerts -> lower score.
    """
    if list_alerts is None:
        return {"score": 70, "reason": "risk_module_missing"}

    try:
        # if unit_id provided, list alerts for that unit; else list all alerts and count high severity
        resp = list_alerts(unit_id=unit_id) if unit_id else list_alerts()
        alerts = resp.get("alerts", [])
        high = sum(1 for a in alerts if a.get("severity") == "high")
        medium = sum(1 for a in alerts if a.get("severity") == "medium")
        # heuristic mapping
        score = 100 - min(80, high * 25 + medium * 10)
        return {"score": max(0, min(100, int(score))), "details": {"high": high, "medium": medium}, "reason": f"high={high},medium={medium}"}
    except Exception as e:
        return {"score": 60, "reason": f"error:{str(e)}"}


def _compute_collateral_score(farmer_id: Optional[str]) -> Dict[str, Any]:
    """
    Sum equipment estimated values as collateral proxy. If equipment_store present, use 'estimated_value' field if any,
    else use a heuristic on equipment type count.
    """
    try:
        total_value = 0.0
        for eid, rec in (_equipment_store or {}).items():
            val = rec.get("estimated_value") or rec.get("market_value") or 0.0
            total_value += _safe_float(val)
        # Map total_value to score: 0 -> 20, 100k -> 60, 500k -> 90+
        if total_value <= 0:
            score = 20
        elif total_value < 100000:
            score = int(20 + (total_value / 100000) * 40)
        elif total_value < 500000:
            score = int(60 + ((total_value - 100000) / 400000) * 30)
        else:
            score = 95
        return {"score": max(0, min(100, int(score))), "collateral_value_estimate": round(total_value, 2)}
    except Exception:
        return {"score": 40, "collateral_value_estimate": 0.0}


def compute_credit_score(
    farmer_id: Optional[str] = None,
    unit_id: Optional[str] = None,
    market_price_per_quintal: Optional[float] = None,
    weights: Optional[Dict[str, float]] = None
) -> Dict[str, Any]:
    """
    Main function: returns a detailed credit eligibility result:
    {
      score: 0-100,
      components: { cashflow_stability: {...}, repayment_capacity: {...}, ... },
      recommended_max_loan: float (conservative),
      verdict: "eligible"/"needs_review"/"not_eligible",
      explainability: ...
    }
    """
    w = DEFAULT_WEIGHTS.copy()
    if weights:
        # normalize supplied weights so they sum to 1
        total = sum(weights.values())
        if total > 0:
            w = {k: float(weights.get(k, w[k])) for k in w}
            s = sum(w.values())
            if s > 0:
                w = {k: v / s for k, v in w.items()}

    # compute components
    cashflow = _compute_cashflow_score(farmer_id)
    repay = _compute_repayment_capacity(unit_id, market_price_per_quintal)
    yield_stab = _compute_yield_stability_score(unit_id)
    risk = _compute_risk_profile_score(farmer_id, unit_id)
    collat = _compute_collateral_score(farmer_id)

    # weighted aggregation
    comp_map = {
        "cashflow_stability": cashflow,
        "repayment_capacity": repay,
        "yield_stability": yield_stab,
        "risk_profile": risk,
        "collateral": collat
    }

    total_score = 0.0
    for k, comp in comp_map.items():
        total_score += w.get(k, 0) * _safe_float(comp.get("score", 60))

    total_score = int(round(max(0, min(100, total_score))))

    # recommended loan: conservative fraction of annual surplus / collateral
    annual_surplus = _safe_float(repay.get("annual_surplus_estimate", 0))
    collateral_value = _safe_float(collat.get("collateral_value_estimate", 0))
    # recommended loan = min(annual_surplus * 2, collateral_value * 0.5)
    rec_from_surplus = annual_surplus * 2
    rec_from_collateral = collateral_value * 0.5 if collateral_value > 0 else 0
    recommended_max_loan = round(min(rec_from_surplus if rec_from_surplus>0 else float("inf"), rec_from_collateral if rec_from_collateral>0 else float("inf")) if (rec_from_surplus>0 or rec_from_collateral>0) else 0.0, 2)

    # verdict mapping
    if total_score >= 75 and recommended_max_loan > 0:
        verdict = "eligible"
    elif total_score >= 55:
        verdict = "needs_review"
    else:
        verdict = "not_eligible"

    result = {
        "farmer_id": farmer_id,
        "unit_id": unit_id,
        "overall_score": total_score,
        "components": comp_map,
        "weights_used": w,
        "recommended_max_loan": recommended_max_loan,
        "verdict": verdict,
        "generated_at": datetime.utcnow().isoformat()
    }

    # persist application snapshot
    key = f"app_{farmer_id or 'unknown'}_{int(datetime.utcnow().timestamp())}"
    with _credit_lock:
        _credit_app_store[key] = result

    return result


def fetch_recent_applications(limit: int = 10) -> List[Dict[str, Any]]:
    with _credit_lock:
        items = list(_credit_app_store.values())
    items_sorted = sorted(items, key=lambda x: x.get("generated_at", ""), reverse=True)
    return items_sorted[:limit]
