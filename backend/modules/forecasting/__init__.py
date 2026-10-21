"""SALES FORECASTING  -  owner: G Yaswanth Sai & FinPilot AI Team

The forecasts come from trained Prophet models (one per product sub-category).
Runtime reads `forecast_bundle.json`. When users upload updated item lists, price changes,
or new stock CSVs via the UI, a custom overlay is persisted in `data/forecast_custom.json`
and dynamically re-projects next-week and 4-week sales across all categories.

Public functions:
    list_sub_categories()            -> ["Accessories", "Appliances", ...]
    get_groups()                     -> {"Furniture": ["Bookcases", ...], ...}
    get_all_next_week()              -> [{sub_category, week_ending, predicted_sales,
                                          lower_estimate, upper_estimate, category}, ...]
    predict_next_week(sub_category)  -> one dict of the same shape
    get_chart_data(sub_category)     -> {sub_category, category, history, forecast}
    get_summary()                    -> totals, metrics and data notes for the dashboard
    apply_forecast_csv(csv_text)     -> updates projections from uploaded CSV
    reset_custom_forecast()          -> resets back to baseline bundle
    get_sample_forecast_csv()        -> returns downloadable sample CSV template
    is_custom_forecast_active()      -> bool
"""
import copy
import csv
import io
import json
import os
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional

BASE_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = BASE_DIR / "data"
CUSTOM_FORECAST_FILE = DATA_DIR / "forecast_custom.json"

_BUNDLE_PATH = Path(__file__).parent / "forecast_bundle.json"
_BASE_BUNDLE = json.loads(_BUNDLE_PATH.read_text(encoding="utf-8"))

_lock = threading.Lock()
_ITEMS: Dict[str, Any] = {}
_GROUPS: Dict[str, List[str]] = {}
_LOOKUP: Dict[str, str] = {}
_IS_CUSTOM: bool = False
_CUSTOM_FILENAME: Optional[str] = None

GROUP_LABELS: dict = {}


def _label(group: str) -> str:
    return GROUP_LABELS.get(group, group)


def _rebuild_lookup() -> None:
    global _LOOKUP
    _LOOKUP = {name.lower(): name for name in _ITEMS}


def _load_data() -> None:
    global _ITEMS, _GROUPS, _IS_CUSTOM, _CUSTOM_FILENAME
    with _lock:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        # Deepcopy baseline
        base_items = copy.deepcopy(_BASE_BUNDLE["items"])
        base_groups = copy.deepcopy(_BASE_BUNDLE["groups"])

        if CUSTOM_FORECAST_FILE.exists():
            try:
                with open(CUSTOM_FORECAST_FILE, "r", encoding="utf-8") as f:
                    custom = json.load(f)
                custom_items = custom.get("items", {})
                custom_groups = custom.get("groups", {})
                _CUSTOM_FILENAME = custom.get("filename")

                # Merge custom items over base items
                for k, v in custom_items.items():
                    base_items[k] = v

                # Merge custom groups
                for grp, items in custom_groups.items():
                    if grp not in base_groups:
                        base_groups[grp] = []
                    for it in items:
                        if it not in base_groups[grp]:
                            base_groups[grp].append(it)

                _ITEMS = base_items
                _GROUPS = base_groups
                _IS_CUSTOM = True
                _rebuild_lookup()
                return
            except Exception:
                pass

        _ITEMS = base_items
        _GROUPS = base_groups
        _IS_CUSTOM = False
        _CUSTOM_FILENAME = None
        _rebuild_lookup()


# Initialize on import
_load_data()


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
        "predicted_sales": round(float(f["predicted"]), 2),
        "lower_estimate": round(float(f["lower"]), 2),
        "upper_estimate": round(float(f["upper"]), 2),
        "category": _label(it["category"]),
    }


def list_sub_categories() -> list:
    return sorted(_ITEMS.keys())


def get_groups() -> dict:
    return {_label(g): list(v) for g, v in _GROUPS.items()}


def get_all_next_week() -> list:
    return [_next_week_row(s) for s in sorted(_ITEMS.keys())]


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
    meta = dict(_BASE_BUNDLE["meta"])
    if _IS_CUSTOM:
        meta["is_custom_upload"] = True
        if _CUSTOM_FILENAME:
            meta["custom_filename"] = _CUSTOM_FILENAME

    return {
        "meta": meta,
        "metrics": dict(_BASE_BUNDLE["metrics"]),
        "week_ending": rows[0]["week_ending"] if rows else "2019-01-06",
        "next_week_total": round(sum(r["predicted_sales"] for r in rows), 2),
        "next_4_weeks_total": round(four_week_total, 2),
        "sub_category_count": len(rows),
        "is_custom": _IS_CUSTOM,
        "custom_filename": _CUSTOM_FILENAME,
    }


def is_custom_forecast_active() -> bool:
    return _IS_CUSTOM


def reset_custom_forecast() -> dict:
    with _lock:
        if CUSTOM_FORECAST_FILE.exists():
            try:
                CUSTOM_FORECAST_FILE.unlink()
            except Exception:
                pass
    _load_data()
    return {"reset": True, "summary": get_summary()}


def get_sample_forecast_csv() -> str:
    return (
        "sub_category,category,price_change_pct,stock,predicted_sales\n"
        "Accessories,Technology,5,250,1120.00\n"
        "Chairs,Furniture,-3,180,1650.00\n"
        "Phones,Technology,10,300,2100.00\n"
        "Storage,Office Supplies,0,400,950.00\n"
        "Binders,Office Supplies,2,350,820.00\n"
        "Paper,Office Supplies,-5,500,740.00\n"
        "Smartwatches,Technology,0,150,1280.00\n"
        "Ergonomic Desks,Furniture,0,80,1850.00\n"
    )


def apply_forecast_csv(csv_text: str, filename: str = "custom_inventory.csv") -> dict:
    """Parses user CSV and recalculates item projections dynamically.
    
    Supports:
    - price changes: price_change_pct (+/-%) or price / old_price
    - stock/inventory updates
    - direct predicted sales adjustments
    - new items / new product categories
    """
    if not csv_text or not csv_text.strip():
        raise ValueError("Uploaded CSV file is empty.")

    reader = csv.DictReader(io.StringIO(csv_text.strip()))
    if not reader.fieldnames:
        raise ValueError("CSV has no header row.")

    # Normalize header mapping
    field_map = {col.lower().strip().replace(" ", "_").replace("-", "_"): col for col in reader.fieldnames}

    def get_field(row: dict, *candidates: str) -> Optional[str]:
        for c in candidates:
            orig = field_map.get(c)
            if orig and row.get(orig) is not None:
                val = str(row[orig]).strip()
                if val:
                    return val
        return None

    # Load fresh baseline to apply modifications on
    base_items = copy.deepcopy(_BASE_BUNDLE["items"])
    base_groups = copy.deepcopy(_BASE_BUNDLE["groups"])
    base_lookup = {k.lower(): k for k in base_items}

    # Reference dates and sample history from existing bundle
    sample_sub = list(base_items.keys())[0]
    sample_dates = [f["date"] for f in base_items[sample_sub]["forecast"]]
    sample_hist = base_items[sample_sub]["history"]

    items_updated = 0
    new_items_added = 0

    for row_idx, row in enumerate(reader, start=1):
        item_name = get_field(row, "sub_category", "subcategory", "item", "product", "product_name", "name")
        if not item_name:
            continue

        category = get_field(row, "category", "group", "department")

        # Parse numerical columns
        price_change_pct = get_field(row, "price_change_pct", "price_change", "change_pct", "adjustment_pct")
        price = get_field(row, "price", "new_price", "unit_price")
        old_price = get_field(row, "old_price", "previous_price", "base_price")
        stock = get_field(row, "stock", "stock_units", "inventory", "units")
        predicted_sales = get_field(row, "predicted_sales", "projected_sales", "forecast_sales", "sales", "predicted")

        # Check if item exists in baseline
        matched_key = base_lookup.get(item_name.lower())

        if matched_key:
            target_item = base_items[matched_key]
            current_p0 = float(target_item["forecast"][0]["predicted"])

            if predicted_sales is not None:
                try:
                    val = float(predicted_sales.replace("$", "").replace(",", ""))
                    factor = val / max(1.0, current_p0)
                except ValueError:
                    factor = 1.0
            elif price_change_pct is not None:
                try:
                    pct = float(price_change_pct.replace("%", "").replace("+", ""))
                    factor = 1.0 + (pct / 100.0)
                except ValueError:
                    factor = 1.0
            elif price is not None and old_price is not None:
                try:
                    p_new = float(price.replace("$", "").replace(",", ""))
                    p_old = float(old_price.replace("$", "").replace(",", ""))
                    factor = p_new / max(0.01, p_old)
                except ValueError:
                    factor = 1.0
            elif price is not None:
                # Moderate price adjustment
                try:
                    p_val = float(price.replace("$", "").replace(",", ""))
                    factor = max(0.5, min(2.5, p_val / 100.0))
                except ValueError:
                    factor = 1.0
            else:
                factor = 1.0

            # Scale forecast points and uncertainty bounds
            updated_forecast = []
            for pt in target_item["forecast"]:
                new_pred = round(float(pt["predicted"]) * factor, 2)
                new_lower = round(float(pt["lower"]) * factor, 2)
                new_upper = round(float(pt["upper"]) * factor, 2)
                updated_forecast.append({
                    "date": pt["date"],
                    "predicted": new_pred,
                    "lower": new_lower,
                    "upper": new_upper,
                })
            target_item["forecast"] = updated_forecast

            if category:
                target_item["category"] = category.strip()
                # Ensure in groups
                cat = category.strip()
                if cat not in base_groups:
                    base_groups[cat] = []
                if matched_key not in base_groups[cat]:
                    base_groups[cat].append(matched_key)

            items_updated += 1

        else:
            # Brand new item
            cat_name = category.strip() if category else "New Additions"
            p0 = 1000.0
            if predicted_sales is not None:
                try:
                    p0 = float(predicted_sales.replace("$", "").replace(",", ""))
                except ValueError:
                    p0 = 1000.0
            elif price is not None and stock is not None:
                try:
                    p_val = float(price.replace("$", "").replace(",", ""))
                    s_val = float(stock.replace(",", ""))
                    p0 = p_val * min(s_val, 30.0)
                except ValueError:
                    p0 = 1000.0
            elif price is not None:
                try:
                    p0 = float(price.replace("$", "").replace(",", "")) * 15.0
                except ValueError:
                    p0 = 1000.0

            clean_name = item_name.strip()
            new_forecast = [
                {
                    "date": sample_dates[0] if len(sample_dates) > 0 else "2019-01-06",
                    "predicted": round(p0, 2),
                    "lower": round(p0 * 0.72, 2),
                    "upper": round(p0 * 1.32, 2),
                },
                {
                    "date": sample_dates[1] if len(sample_dates) > 1 else "2019-01-13",
                    "predicted": round(p0 * 1.03, 2),
                    "lower": round(p0 * 0.74, 2),
                    "upper": round(p0 * 1.35, 2),
                },
                {
                    "date": sample_dates[2] if len(sample_dates) > 2 else "2019-01-20",
                    "predicted": round(p0 * 0.98, 2),
                    "lower": round(p0 * 0.70, 2),
                    "upper": round(p0 * 1.30, 2),
                },
                {
                    "date": sample_dates[3] if len(sample_dates) > 3 else "2019-01-27",
                    "predicted": round(p0 * 1.06, 2),
                    "lower": round(p0 * 0.76, 2),
                    "upper": round(p0 * 1.40, 2),
                },
            ]

            # Generate synthetic 52 weeks history
            new_history = [
                {
                    "date": h["date"],
                    "sales": round(p0 * (0.8 + 0.35 * (((i * 9) % 13) / 12.0)), 2),
                }
                for i, h in enumerate(sample_hist)
            ]

            base_items[clean_name] = {
                "category": cat_name,
                "history": new_history,
                "forecast": new_forecast,
            }

            if cat_name not in base_groups:
                base_groups[cat_name] = []
            if clean_name not in base_groups[cat_name]:
                base_groups[cat_name].append(clean_name)

            new_items_added += 1

    if items_updated == 0 and new_items_added == 0:
        raise ValueError("No recognized items or sub-categories were found in the uploaded CSV.")

    # Save custom overlay
    save_payload = {
        "filename": filename,
        "items": base_items,
        "groups": base_groups,
    }
    with _lock:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        with open(CUSTOM_FORECAST_FILE, "w", encoding="utf-8") as f:
            json.dump(save_payload, f, indent=2, ensure_ascii=False)

    _load_data()
    summ = get_summary()

    return {
        "success": True,
        "filename": filename,
        "items_updated": items_updated,
        "new_items_added": new_items_added,
        "summary": summ,
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
