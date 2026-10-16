from fastapi import APIRouter, Depends
from app.auth_utils import require_permission
from modules.forecasting import get_forecast

router = APIRouter()


@router.get("")
def forecast(horizon_days: int = 15, user=Depends(require_permission("forecast:read"))):
    return get_forecast(horizon_days)
