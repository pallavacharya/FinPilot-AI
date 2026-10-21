from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import PlainTextResponse
from app.auth_utils import require_permission
from modules.forecasting import (
    get_forecast,
    get_groups,
    list_sub_categories,
    get_all_next_week,
    predict_next_week,
    get_chart_data,
    get_summary,
    apply_forecast_csv,
    reset_custom_forecast,
    get_sample_forecast_csv,
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


@router.post("/upload")
async def upload_forecast_csv(
    file: UploadFile = File(...),
    user=Depends(require_permission("forecast:read")),
):
    if not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV files (.csv) are supported.")
    try:
        content_bytes = await file.read()
        text = content_bytes.decode("utf-8-sig")  # handle UTF-8 with BOM if from Excel
        res = apply_forecast_csv(text, filename=file.filename)
        return res
    except UnicodeDecodeError:
        try:
            text = content_bytes.decode("latin-1")
            res = apply_forecast_csv(text, filename=file.filename)
            return res
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Failed to read CSV encoding: {e}")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process forecast CSV: {e}")


@router.post("/reset")
def reset_forecast(user=Depends(require_permission("forecast:read"))):
    return reset_custom_forecast()


@router.get("/sample-csv")
def download_sample_csv(user=Depends(require_permission("forecast:read"))):
    csv_text = get_sample_forecast_csv()
    return PlainTextResponse(
        content=csv_text,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=forecast_template.csv"},
    )
