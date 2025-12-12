# backend/app/services/farmer/germination_service.py
"""
Germination Rate Prediction Service (Feature 326)

- Pulls historical germination tests from seed_service (if available).
- Provides:
  * rule_based_predict(batch_id, context) -> {predicted_pct, confidence, reasons}
  * train_linear_model(batch_id) -> stores a small per-batch linear model (in-memory)
  * predict_with_model(batch_id, context) -> uses trained model if present
  * batch_predict_for_farmer(farmer_id, contexts)
- Context keys supported (optional):
  - sample_moisture_pct
  - storage_days (days between received and planting)
  - temperature_c_avg (recent average)
  - seed_age_days (since harvest)
  - treatment_present (bool)
- Note: This is a stubbed lightweight predictor meant for engineering & UI; can be replaced by a real ML pipeline later.
"""

from datetime import datetime
from threading import Lock
from typing import Dict, Any, List, Optional
import math

# defensive import for seed tests
try:
    from app.services.farmer.seed_service import list_germination_tests, get_seed_batch, historical_germination_stats
except Exception:
    # fallbacks
    list_germination_tests = lambda batch_id: []
    get_seed_batch = lambda batch_id: {}
    historical_germination_stats = lambda batch_id: {"count": 0, "mean": None, "stdev": None}

_lock = Lock()

_models: Dict[str, Dict[str, Any]] = {}  # batch_id -> {"coef": {...}, "intercept": float, "trained_at": iso}

def _now_iso():
    return datetime.utcnow().isoformat()

# -----------------------
# Simple rule-based predictor
# -----------------------
def rule_based_predict(batch_id: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Heuristics:
      - Use latest historic germination pct if available (high confidence)
      - Penalize for high storage_days (>90 days) by -10%
      - Penalize for high moisture in seed (>14%) by -15% (mold risk)
      - Adjust by treatment presence (+5%)
      - Clamp 0..100
    Returns: { batch_id, predicted_germ_pct, confidence (0..1), reasons }
    """
    ctx = context or {}
    hist_stats = historical_germination_stats(batch_id)
    base = hist_stats.get("mean")
    reasons = []
    confidence = 0.3

    if base is None:
        # try seed batch defaults
        batch = get_seed_batch(batch_id)
        variety = (batch.get("variety") or "").lower() if isinstance(batch, dict) else ""
        defaults = {"wheat": 85.0, "rice": 80.0, "maize": 88.0, "soybean": 82.0}
        base = defaults.get(variety, 70.0)
        reasons.append("used_variety_default")
        confidence = 0.25
    else:
        reasons.append("used_historical_mean")
        confidence = 0.6 if hist_stats.get("count",0) >= 2 else 0.45

    pred = float(base)

    # storage_days penalty
    storage_days = ctx.get("storage_days")
    if storage_days is not None:
        storage_days = float(storage_days)
        if storage_days > 90:
            penal = min(20.0, (storage_days - 90) / 30.0 * 5.0)  # ~5% per month beyond 90d, capped
            pred -= penal
            reasons.append(f"storage_penalty_{round(penal,1)}%")
            confidence -= 0.05

    # moisture penalty
    moisture = ctx.get("sample_moisture_pct")
    if moisture is not None:
        moisture = float(moisture)
        if moisture > 14.0:
            penal = min(25.0, (moisture - 14.0) * 1.5)
            pred -= penal
            reasons.append(f"high_moisture_penalty_{round(penal,1)}%")
            confidence -= 0.08
        elif moisture < 8.0:
            # too dry — small penalty
            pred -= 3.0
            reasons.append("too_dry_penalty_3%")
            confidence -= 0.02

    # treatment boost
    if ctx.get("treatment_present"):
        pred += 5.0
        reasons.append("treatment_boost_+5%")
        confidence += 0.03

    # temperature effect (very coarse)
    temp = ctx.get("temperature_c_avg")
    if temp is not None:
        try:
            t = float(temp)
            if t < 10 or t > 35:
                pred -= 5.0
                reasons.append("temp_out_of_range_penalty")
                confidence -= 0.03
        except Exception:
            pass

    pred = max(0.0, min(100.0, round(pred,2)))
    confidence = max(0.05, min(0.99, round(confidence, 2)))

    return {"batch_id": batch_id, "predicted_germ_pct": pred, "confidence": confidence, "reasons": reasons, "method": "rule_based"}

# -----------------------
# Tiny linear model trainer (OLS) using features derived from tests
# -----------------------
def _extract_feature_vector_from_test(test: Dict[str, Any], batch_meta: Dict[str, Any]) -> Optional[Dict[str, float]]:
    """
    Build features from a single germination test record + batch metadata.
    Supported features:
      - sample_moisture_pct (if present)
      - days_since_received (if test.date and batch.date_received present)
      - seed_age_days (from batch.metadata if present)
      - treatment_flag (1 if treatment present)
    Returns dict of features or None if insufficient.
    """
    features = {}
    # germination_pct is label
    if test.get("germination_pct") is None:
        return None
    # moisture
    if test.get("moisture_pct") is not None:
        features["moisture"] = float(test.get("moisture_pct"))
    # days since received
    try:
        test_date = datetime.fromisoformat(test.get("date")).date()
        dr = batch_meta.get("date_received")
        if dr:
            try:
                received = datetime.fromisoformat(dr).date()
                features["days_since_received"] = float((test_date - received).days)
            except Exception:
                pass
    except Exception:
        pass
    # seed_age_days in metadata
    try:
        if batch_meta.get("metadata", {}).get("seed_age_days") is not None:
            features["seed_age_days"] = float(batch_meta.get("metadata", {}).get("seed_age_days"))
    except Exception:
        pass
    # treatment flag
    if batch_meta.get("treatment"):
        features["treatment"] = 1.0
    # require at least one feature other than label
    return features if len(features) > 0 else features  # allow model on single feature too

def train_linear_model(batch_id: str) -> Dict[str, Any]:
    """
    Train a simple OLS linear model for the batch using historic germination tests.
    Model: germination_pct = intercept + sum(coef_i * feature_i)
    Stores coefficients in _models[batch_id].
    Returns model summary or error.
    """
    tests = list_germination_tests(batch_id) or []
    batch_meta = get_seed_batch(batch_id) or {}
    # build dataset
    X = []
    y = []
    feature_names = set()
    for t in tests:
        fv = _extract_feature_vector_from_test(t, batch_meta)
        if fv is None:
            continue
        X.append(fv)
        y.append(float(t.get("germination_pct", 0.0)))
        feature_names.update(fv.keys())

    feature_names = sorted(feature_names)
    if not feature_names or len(y) < 2:
        return {"error": "insufficient_data", "count_tests": len(tests)}

    # build matrix
    # convert X dicts to list vectors
    Xmat = []
    for row in X:
        vec = [float(row.get(f, 0.0)) for f in feature_names]
        Xmat.append(vec)
    # compute OLS using normal equations: coef = (X^T X)^-1 X^T y
    # We'll implement naive numeric linear algebra (sufficient for small features)
    try:
        # build XtX
        m = len(feature_names)
        XtX = [[0.0]*m for _ in range(m)]
        Xty = [0.0]*m
        n = len(Xmat)
        for i in range(n):
            xi = Xmat[i]
            yi = y[i]
            for a in range(m):
                Xty[a] += xi[a] * yi
                for b in range(m):
                    XtX[a][b] += xi[a] * xi[b]
        # add small ridge to diagonal for stability
        ridge = 1e-6
        for i in range(m):
            XtX[i][i] += ridge
        # solve linear system XtX * coef = Xty (use gaussian elimination)
        # Augmented matrix
        A = [row[:] + [Xty[i]] for i, row in enumerate(XtX)]
        # Gaussian elimination
        M = m
        for col in range(M):
            # pivot
            pivot = col
            # find non-zero pivot
            if abs(A[pivot][col]) < 1e-12:
                for r in range(col+1, M):
                    if abs(A[r][col]) > abs(A[pivot][col]):
                        pivot = r
            A[col], A[pivot] = A[pivot], A[col]
            pv = A[col][col]
            if abs(pv) < 1e-12:
                continue
            # normalize
            invpv = 1.0 / pv
            for c in range(col, M+1):
                A[col][c] *= invpv
            # eliminate
            for r in range(M):
                if r == col: continue
                factor = A[r][col]
                if abs(factor) < 1e-12: continue
                for c in range(col, M+1):
                    A[r][c] -= factor * A[col][c]
        coef = [A[i][M] for i in range(M)]
        # intercept via mean(y) - sum(coef * mean(x))
        means = [ sum(Xmat[i][j] for i in range(len(Xmat))) / len(Xmat) for j in range(M) ]
        mean_y = sum(y) / len(y)
        intercept = mean_y - sum(coef[j]*means[j] for j in range(M))
        model = {"feature_names": feature_names, "coef": {feature_names[i]: round(coef[i],6) for i in range(M)}, "intercept": round(intercept,6), "trained_at": _now_iso(), "n_samples": len(y)}
        with _lock:
            _models[batch_id] = model
        return {"status": "trained", "model": model}
    except Exception as e:
        return {"error": "training_failed", "reason": str(e)}

# -----------------------
# Prediction using trained model (if exists)
# -----------------------
def predict_with_model(batch_id: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    model = _models.get(batch_id)
    if not model:
        return {"error": "model_not_found"}
    ctx = context or {}
    # build feature vector in model feature order
    fnames = model["feature_names"]
    vec = []
    for f in fnames:
        if f == "moisture":
            vec.append(float(ctx.get("sample_moisture_pct", 0.0)))
        elif f == "days_since_received":
            vec.append(float(ctx.get("storage_days", 0.0)))
        elif f == "seed_age_days":
            vec.append(float(ctx.get("seed_age_days", 0.0)))
        elif f == "treatment":
            vec.append(1.0 if ctx.get("treatment_present") else 0.0)
        else:
            vec.append(float(ctx.get(f, 0.0)))
    # compute prediction
    pred = float(model.get("intercept",0.0)) + sum(model["coef"].get(f,0.0) * vec[i] for i,f in enumerate(fnames))
    # confidence heuristic: based on n_samples
    n = model.get("n_samples",1)
    conf = min(0.95, 0.3 + 0.1 * math.log(max(2,n)))
    pred = max(0.0, min(100.0, round(pred,2)))
    return {"batch_id": batch_id, "predicted_germ_pct": pred, "confidence": round(conf,2), "method": "linear_model", "model_meta": {"n_samples": n}}

# -----------------------
# Public prediction wrapper
# -----------------------
def predict_germination(batch_id: str, context: Optional[Dict[str, Any]] = None, prefer_model: bool = True) -> Dict[str, Any]:
    """
    Predict germination for a batch:
      - if prefer_model and model exists -> model prediction
      - else fallback to rule-based
      - return both if available for comparison
    """
    ctx = context or {}
    if prefer_model and batch_id in _models:
        try:
            mres = predict_with_model(batch_id, ctx)
            # may also compute rule-based and provide both
            rres = rule_based_predict(batch_id, ctx)
            return {"from_model": mres, "from_rule": rres, "preferred": "model"}
        except Exception:
            return {"from_rule": rule_based_predict(batch_id, ctx), "preferred": "rule"}
    else:
        r = rule_based_predict(batch_id, ctx)
        modelinfo = _models.get(batch_id)
        return {"from_rule": r, "model_present": bool(modelinfo), "preferred": "rule"}

# -----------------------
# Utilities
# -----------------------
def list_trained_models() -> Dict[str, Any]:
    with _lock:
        return {"count": len(_models), "models": {k:v for k,v in _models.items()}}
