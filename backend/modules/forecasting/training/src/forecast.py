import os
import pandas as pd
from prophet.serialize import model_from_json

BASE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
MODEL_DIR = os.path.join(BASE_DIR, 'outputs', 'models')
WEEKLY_FILE = os.path.join(BASE_DIR, 'outputs', 'weekly_sales.csv')
NEXT_WEEK_FILE = os.path.join(BASE_DIR, 'outputs', 'forecast_next_week.csv')


def _load_model(sub_category):
    fname = sub_category.replace(' ', '_')
    with open(os.path.join(MODEL_DIR, f'prophet_{fname}.json')) as f:
        return model_from_json(f.read())


def list_sub_categories():
    return sorted(f[8:-5].replace('_', ' ') for f in os.listdir(MODEL_DIR) if f.startswith('prophet_'))


def predict_next_week(sub_category):
    """Next week's predicted sales (with a range) for one sub-category."""
    m = _load_model(sub_category)
    f = m.predict(m.make_future_dataframe(periods=1, freq='W')).tail(1)
    return {
        'sub_category': sub_category,
        'week_ending': str(f['ds'].iloc[0].date()),
        'predicted_sales': round(max(f['yhat'].iloc[0], 0), 2),
        'lower_estimate': round(max(f['yhat_lower'].iloc[0], 0), 2),
        'upper_estimate': round(max(f['yhat_upper'].iloc[0], 0), 2),
    }


def get_chart_data(sub_category, history_weeks=52, forecast_weeks=4):
    """Past sales + future forecast for one sub-category, ready for a line chart."""
    m = _load_model(sub_category)
    pred = m.predict(m.make_future_dataframe(periods=forecast_weeks, freq='W')).tail(forecast_weeks)

    weekly = pd.read_csv(WEEKLY_FILE, parse_dates=['date'])
    hist = (weekly[weekly['sub_category'] == sub_category]
            .sort_values('date').tail(history_weeks))

    return {
        'sub_category': sub_category,
        'history': [{'date': str(d.date()), 'sales': round(float(v), 2)}
                    for d, v in zip(hist['date'], hist['sales'])],
        'forecast': [{'date': str(r.ds.date()),
                      'predicted': round(max(r.yhat, 0), 2),
                      'lower': round(max(r.yhat_lower, 0), 2),
                      'upper': round(max(r.yhat_upper, 0), 2)}
                     for r in pred.itertuples()],
    }


def get_all_next_week():
    """Next week's forecast for every sub-category, ready for a bar chart."""
    return pd.read_csv(NEXT_WEEK_FILE).to_dict(orient='records')


if __name__ == '__main__':
    print(predict_next_week('Chairs'))
    print(list_sub_categories())