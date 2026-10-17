# Forecasting: training assets

Yaswanth's work, kept here for reference and retraining. The backend does NOT use these files directly;
it uses `../forecast_bundle.json`.

- `Model_training.ipynb`  trains and evaluates the models (Prophet vs XGBoost vs "same as last week")
- `outputs/models/`       the 17 trained Prophet models (one JSON per sub-category)
- `outputs/weekly_sales.csv`, `outputs/forecast_next_week.csv`  weekly sales per sub-category + category map
- `src/forecast.py`       Yaswanth's original functions (they run Prophet live)
- `build_forecast_bundle.py`  turns the models into `../forecast_bundle.json` (fixed random seed)

## After retraining
    cd backend/modules/forecasting/training
    pip install -r requirements.txt      # use a separate virtual environment, not the backend one
    python build_forecast_bundle.py
Then commit the new `forecast_bundle.json`.

The raw dataset `AI_dataset.csv` is not in the repo (it is only needed to retrain in the notebook).
