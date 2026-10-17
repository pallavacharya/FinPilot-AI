"""Precompute everything the dashboard needs from Yaswanth's trained Prophet models.

Run this ONLY when the models are retrained (needs `pip install -r requirements.txt` here).
The backend itself never imports Prophet: it just reads the JSON file this script writes.

    cd backend/modules/forecasting/training
    python build_forecast_bundle.py

Why precompute: Prophet draws random samples for its lower/upper range, so calling it live gives
slightly different ranges on every call (the chart and the summary card could disagree).
Here we fix the random seed once, so every number the dashboard shows comes from one consistent run.
"""
import json
import os
from datetime import datetime, timezone

import numpy as np
import pandas as pd
from prophet.serialize import model_from_json

HERE = os.path.dirname(os.path.abspath(__file__))
MODEL_DIR = os.path.join(HERE, "outputs", "models")
WEEKLY_FILE = os.path.join(HERE, "outputs", "weekly_sales.csv")
NEXT_WEEK_FILE = os.path.join(HERE, "outputs", "forecast_next_week.csv")  # only used for the sub-category -> category map
OUT_FILE = os.path.join(HERE, "..", "forecast_bundle.json")

HISTORY_WEEKS = 52
FORECAST_WEEKS = 4
SEED = 0

# Backtest numbers copied from the printed outputs in Model_training.ipynb
# (time-based split: the last 12 weeks held out, 17 sub-categories).
METRICS = {
    "backtest": "last 12 weeks held out",
    "model": "Prophet",
    "rmse": 1708.31,
    "wape_pct": 70.44,
    "baseline_rmse": 2386.80,
    "baseline_wape_pct": 97.43,
    "baseline_name": "next week = last week",
    "note": "WAPE = total absolute error / total sales. Weekly sales per sub-category are noisy, so treat the range as the answer, not the single number.",
}


def main():
    weekly = pd.read_csv(WEEKLY_FILE, parse_dates=["date"])
    cat_map = pd.read_csv(NEXT_WEEK_FILE).set_index("sub_category")["category"].to_dict()

    items = {}
    for fname in sorted(os.listdir(MODEL_DIR)):
        if not (fname.startswith("prophet_") and fname.endswith(".json")):
            continue
        sub = fname[len("prophet_"):-len(".json")].replace("_", " ")
        with open(os.path.join(MODEL_DIR, fname), encoding="utf-8") as f:
            model = model_from_json(f.read())

        np.random.seed(SEED)  # fixed seed -> reproducible lower/upper range
        future = model.make_future_dataframe(periods=FORECAST_WEEKS, freq="W")
        pred = model.predict(future).tail(FORECAST_WEEKS)

        hist = weekly[weekly["sub_category"] == sub].sort_values("date").tail(HISTORY_WEEKS)
        items[sub] = {
            "category": cat_map[sub],
            "history": [{"date": str(d.date()), "sales": round(float(v), 2)}
                        for d, v in zip(hist["date"], hist["sales"])],
            "forecast": [{"date": str(r.ds.date()),
                          "predicted": round(float(max(r.yhat, 0)), 2),
                          "lower": round(float(max(r.yhat_lower, 0)), 2),
                          "upper": round(float(max(r.yhat_upper, 0)), 2)}
                         for r in pred.itertuples()],
        }

    groups = {}
    for sub, it in items.items():
        groups.setdefault(it["category"], []).append(sub)
    groups = {g: sorted(v) for g, v in sorted(groups.items())}

    bundle = {
        "meta": {
            "dataset": "Superstore sales, 2015-2018 (demo data)",
            "currency": "USD",
            "unit_label": "Sales ($)",
            "data_through": str(weekly["date"].max().date()),
            "history_weeks": HISTORY_WEEKS,
            "forecast_weeks": FORECAST_WEEKS,
            "range_note": "lower/upper estimate = Prophet's default 80% uncertainty interval",
            "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        },
        "metrics": METRICS,
        "groups": groups,
        "items": items,
    }
    with open(OUT_FILE, "w", encoding="utf-8") as f:
        json.dump(bundle, f, indent=1)
    print(f"wrote {os.path.normpath(OUT_FILE)}: {len(items)} sub-categories in {len(groups)} groups")


if __name__ == "__main__":
    main()
