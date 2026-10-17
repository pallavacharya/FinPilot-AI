from fastapi import APIRouter, Depends, HTTPException, Query
from app.auth_utils import require_permission
from modules.forecasting import (
    get_forecast,
    get_groups,
    list_sub_categories,
    get_all_next_week,
    predict_next_week,
    get_chart_data,
    get_summary,
)

router = APIRouter()


@router.get("")
def forecast(horizon_days: int = 15, user=Depends(require_permission("forecast:read"))):
    # Legacy sample data for the Overview KPI card (see modules/forecasting/__init__.py).
    return get_forecast(horizon_days)


@router.get("/summary")
def summary(user=Depends(require_permission("forecast:read"))):
    return get_summary()


@router.get("/categories")
def categories(user=Depends(require_permission("forecast:read"))):
    return {"groups": get_groups(), "sub_categories": list_sub_categories()}


@router.get("/next-week")
def next_week_all(user=Depends(require_permission("forecast:read"))):
    return {"items": get_all_next_week()}


@router.get("/predict")
def next_week_one(item: str = Query(..., min_length=1), user=Depends(require_permission("forecast:read"))):
    try:
        return predict_next_week(item)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/chart")
def chart(item: str = Query(..., min_length=1), user=Depends(require_permission("forecast:read"))):
    try:
        return get_chart_data(item)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
