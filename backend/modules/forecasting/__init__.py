"""SALES FORECASTING  -  owner: G Yaswanth Sai

Replace the body of get_forecast() with your trained Prophet + XGBoost output.
Keep the function name, the argument, and the return keys EXACTLY as below -
the dashboard reads these keys. Add your own files/folders next to this one.
"""

# --- sample data (delete once the real model is connected) ---
_SAMPLE_ACTUAL = [42, 45, 41, 48, 52, 50, 55, 58, 54, 60, 63, 61, 66, 68]


def get_forecast(horizon_days: int = 15) -> dict:
    """Return the sales forecast.

    Returns:
        {
          "horizon_days": int,            # how many days ahead
          "mape": float,                  # backtest MAPE in %, e.g. 7.9
          "rmse": float,                  # backtest RMSE, e.g. 4210
          "actual": [float, ...],         # recent real sales (same unit as forecast)
          "forecast": [float, ...],       # predicted sales, length == horizon_days
          "next_30d_total_inr": int,      # predicted total for next 30 days, in rupees
        }
    """
    last = _SAMPLE_ACTUAL[-1]
    return {
        "horizon_days": horizon_days,
        "mape": 7.9,
        "rmse": 4210,
        "actual": _SAMPLE_ACTUAL,
        "forecast": [round(last + i * 1.7, 1) for i in range(horizon_days)],
        "next_30d_total_inr": 1840000,
    }
