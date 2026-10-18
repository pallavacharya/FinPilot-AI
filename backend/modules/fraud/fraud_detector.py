from pathlib import Path
import joblib
import numpy as np
import pandas as pd
BASE_DIR = Path(__file__).resolve().parent
MODEL_PATH = BASE_DIR / "models" / "isolation_forest.joblib"
FEATURES = [
    "amount",
    "transaction_frequency",
    "average_amount",
    "time_interval_minutes",
    "location_change",
    "device_change",
]
BOOL_COLS = ["location_change", "device_change"]
SUSPICIOUS_THRESHOLD = 50
_model = None
def _to_dataframe(data) -> pd.DataFrame:
    if isinstance(data, pd.DataFrame):
        df = data.copy()
    elif isinstance(data, dict):
        df = pd.DataFrame([data])
    elif isinstance(data, (list, tuple)):
        df = pd.DataFrame(list(data))
    elif isinstance(data, (str, Path)) or hasattr(data, "read"):
        df = pd.read_csv(data)
    else:
        raise ValueError("Unsupported input type; send a CSV, DataFrame, dict or list of dicts.")
    if df.empty:
        raise ValueError("No transactions received.")
    return df.reset_index(drop=True)
def _to_int_flag(series: pd.Series) -> pd.Series:
    """Accepts True/False, 1/0, 'true'/'false', 'yes'/'no'."""
    if not (pd.api.types.is_bool_dtype(series) or pd.api.types.is_numeric_dtype(series)):
        mapping = {"true": 1, "false": 0, "1": 1, "0": 0, "yes": 1, "no": 0}
        series = series.astype(str).str.strip().str.lower().map(mapping)
        if series.isna().any():
            raise ValueError("location_change / device_change must be true/false or 1/0.")
    return series.astype(int)
def prepare_features(df: pd.DataFrame) -> pd.DataFrame:
    missing = [c for c in FEATURES if c not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")
    X = df[FEATURES].copy()
    for col in BOOL_COLS:
        X[col] = _to_int_flag(X[col])
    for col in FEATURES:
        if col not in BOOL_COLS:
            X[col] = pd.to_numeric(X[col], errors="raise")
    if X.isna().any().any():
        raise ValueError("Missing values found in feature columns.")
    return X
def _get_model():
    """Load the saved model once, then reuse it for every request."""
    global _model
    if _model is None:
        if not MODEL_PATH.exists():
            raise FileNotFoundError(
                f"Trained model not found at {MODEL_PATH}. Run `python train_model.py` first."
            )
        _model = joblib.load(MODEL_PATH)
    return _model
def _explain(amount_pts, freq_pts, time_pts, loc, dev, ai_flag) -> list:
    reasons = []
    if amount_pts:
        reasons.append("Amount is much higher than the customer's average")
    if freq_pts:
        reasons.append("High transaction frequency")
    if time_pts:
        reasons.append("Transactions made within a very short time gap")
    if loc:
        reasons.append("Location changed")
    if dev:
        reasons.append("Device changed")
    if ai_flag:
        reasons.append("Flagged as anomaly by the AI model")
    return reasons
def score_transactions(data) -> list:
    df = _to_dataframe(data)
    X = prepare_features(df)
    model = _get_model()

    ai_flag = model.predict(X) == -1                  # True = anomaly
    ai_score = model.decision_function(X)             # lower = more anomalous

    amt, avg = X["amount"], X["average_amount"]
    amount_pts = np.select([amt > avg * 5, amt > avg * 3, amt > avg * 2], [30, 20, 10], 0)
    freq_pts = np.select([X["transaction_frequency"] >= 20,
                          X["transaction_frequency"] >= 10,
                          X["transaction_frequency"] >= 5], [25, 15, 5], 0)
    time_pts = np.select([X["time_interval_minutes"] <= 5,
                          X["time_interval_minutes"] <= 10], [20, 10], 0)
    loc_pts = X["location_change"].to_numpy() * 15
    dev_pts = X["device_change"].to_numpy() * 10
    ai_pts = np.where(ai_flag, 10, 0)

    risk = np.minimum(amount_pts + freq_pts + time_pts + loc_pts + dev_pts + ai_pts, 100)

    n = len(df)
    ids = df["transaction_id"].tolist() if "transaction_id" in df else [None] * n
    customers = df["customer_id"].tolist() if "customer_id" in df else [None] * n
    amounts = X["amount"].tolist()
    risk_list = risk.astype(float).tolist()
    scores = np.round(ai_score, 4).tolist()

    return [
        {
            "transaction_id": ids[i],
            "customer_id": customers[i],
            "amount": amounts[i],
            "risk_score": risk_list[i],
            "status": "SUSPICIOUS" if risk_list[i] >= SUSPICIOUS_THRESHOLD else "NORMAL",
            "ai_flagged": bool(ai_flag[i]),
            "ai_anomaly_score": scores[i],
            "reasons": _explain(amount_pts[i], freq_pts[i], time_pts[i],
                                loc_pts[i], dev_pts[i], ai_flag[i]),
        }
        for i in range(n)
    ]