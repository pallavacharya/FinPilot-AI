"""SALES FORECASTING  -  owner: G Yaswanth Sai

The forecasts come from Yaswanth's trained Prophet models (one per product sub-category).
At runtime this module only reads `forecast_bundle.json`, so it needs NO extra libraries
(no Prophet in the backend). To regenerate the bundle after retraining, see training/README.md.

Public functions (names and return keys follow Yaswanth's original src/forecast.py):
    list_sub_categories()            -> ["Accessories", "Appliances", ...]
    get_groups()                     -> {"Furniture": ["Bookcases", ...], ...}
    get_all_next_week()              -> [{sub_category, week_ending, predicted_sales,
                                          lower_estimate, upper_estimate, category}, ...]
    predict_next_week(sub_category)  -> one dict of the same shape
    get_chart_data(sub_category)     -> {sub_category, category,
                                          history:  [{date, sales}, ...]   (52 weeks),
                                          forecast: [{date, predicted, lower, upper}, ...] (4 weeks)}
    get_summary()                    -> totals, metrics and data notes for the dashboard
Unknown names raise ValueError.
"""
import json
from pathlib import Path

_BUNDLE = json.loads((Path(__file__).parent / "forecast_bundle.json").read_text(encoding="utf-8"))
_ITEMS = _BUNDLE["items"]
_LOOKUP = {name.lower(): name for name in _ITEMS}

# Optional display names for the main groups, e.g. {"Office Supplies": "Office Essentials"}.
# Empty = show the dataset's own category names.
GROUP_LABELS: dict = {}


def _label(group: str) -> str:
    return GROUP_LABELS.get(group, group)


def _resolve(name: str) -> str:
    key = _LOOKUP.get(str(name).strip().lower())
    if key is None:
        raise ValueError(f"Unknown sub-category: {name}")
    return key


def _next_week_row(sub: str) -> dict:
    it = _ITEMS[sub]
    f = it["forecast"][0]
    return {
        "sub_category": sub,
        "week_ending": f["date"],
        "predicted_sales": f["predicted"],
        "lower_estimate": f["lower"],
        "upper_estimate": f["upper"],
        "category": _label(it["category"]),
    }


def list_sub_categories() -> list:
    return sorted(_ITEMS)


def get_groups() -> dict:
    return {_label(g): list(v) for g, v in _BUNDLE["groups"].items()}


def get_all_next_week() -> list:
    return [_next_week_row(s) for s in sorted(_ITEMS)]


def predict_next_week(sub_category: str) -> dict:
    return _next_week_row(_resolve(sub_category))


def get_chart_data(sub_category: str) -> dict:
    sub = _resolve(sub_category)
    it = _ITEMS[sub]
    return {
        "sub_category": sub,
        "category": _label(it["category"]),
        "history": [dict(h) for h in it["history"]],
        "forecast": [dict(f) for f in it["forecast"]],
    }


def get_summary() -> dict:
    rows = get_all_next_week()
    four_week_total = sum(f["predicted"] for it in _ITEMS.values() for f in it["forecast"])
    return {
        "meta": dict(_BUNDLE["meta"]),
        "metrics": dict(_BUNDLE["metrics"]),
        "week_ending": rows[0]["week_ending"],
        "next_week_total": round(sum(r["predicted_sales"] for r in rows), 2),
        "next_4_weeks_total": round(four_week_total, 2),
        "sub_category_count": len(rows),
    }


# ---------------------------------------------------------------------------------------------
# LEGACY: sample data still used by the Overview tab's KPI card until the frontend is switched
# to get_summary(). Safe to delete once the Overview card reads /api/v1/forecast/summary.
# ---------------------------------------------------------------------------------------------
_SAMPLE_ACTUAL = [42, 45, 41, 48, 52, 50, 55, 58, 54, 60, 63, 61, 66, 68]


def get_forecast(horizon_days: int = 15) -> dict:
    last = _SAMPLE_ACTUAL[-1]
    return {
        "horizon_days": horizon_days,
        "mape": 7.9,
        "rmse": 4210,
        "actual": _SAMPLE_ACTUAL,
        "forecast": [round(last + i * 1.7, 1) for i in range(horizon_days)],
        "next_30d_total_inr": 1840000,
    }
