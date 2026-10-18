from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel

from app.auth_utils import require_permission
from modules.fraud import get_flagged_transactions

router = APIRouter()

MAX_UPLOAD_BYTES = 10 * 1024 * 1024  # 10 MB
MAX_ROWS = 20000

# Human review decisions made in the dashboard, layered on top of the model output.
REVIEWS: dict = {}


@router.get("")
def list_flagged(user=Depends(require_permission("fraud:read"))):
    data = get_flagged_transactions()
    txns = []
    for t in data["transactions"]:
        t = dict(t)
        if t["id"] in REVIEWS:
            t["status"] = REVIEWS[t["id"]]
        txns.append(t)
    pending = [t for t in txns if t["status"] == "pending"]
    return {"count": len(pending), "total_scanned": data["total_scanned"], "transactions": txns}


class ReviewRequest(BaseModel):
    transaction_id: str
    decision: str  # "clear" | "escalate"


@router.post("/review")
def review_transaction(payload: ReviewRequest, user=Depends(require_permission("fraud:approve"))):
    REVIEWS[payload.transaction_id] = "cleared" if payload.decision == "clear" else "escalated"
    return {"transaction_id": payload.transaction_id, "decision": payload.decision, "reviewed_by": user["user_id"]}


def _process_and_score_csv(filename: str, content_str: str, user_id: str) -> dict:
    import io
    try:
        import pandas as pd
    except ImportError:
        raise RuntimeError("Fraud model packages are not installed. Run pip install -r backend/requirements.txt.")

    from modules.fraud import score_transactions_lazy
    from modules.fraud.storage import save_batch

    try:
        df = pd.read_csv(io.StringIO(content_str))
    except Exception as e:
        raise ValueError(f"Failed to parse CSV: {e}")

    if df.empty:
        raise ValueError("No transactions received.")

    if len(df) > MAX_ROWS:
        raise ValueError(f"File contains too many rows (maximum {MAX_ROWS:,}).")

    scored_list = score_transactions_lazy(df)

    DETAIL_COLS = ["transaction_datetime", "location", "device", "payment_method"]
    for i, r in enumerate(scored_list):
        row_details = {}
        for col in DETAIL_COLS:
            if col in df.columns:
                val = df.iloc[i][col]
                if pd.notna(val) and val != "":
                    row_details[col] = str(val) if not isinstance(val, (int, float, bool)) else val
        r["details"] = row_details
        r["orig_index"] = i

    # Sort batch:
    # 1. SUSPICIOUS rows first, then NORMAL rows;
    # 2. inside each group: risk_score descending;
    # 3. ties: ai_anomaly_score ascending (more anomalous first), then amount descending, then original file order.
    sorted_tx = sorted(
        scored_list,
        key=lambda r: (
            0 if r["status"] == "SUSPICIOUS" else 1,
            -r["risk_score"],
            r["ai_anomaly_score"],
            -r["amount"],
            r["orig_index"],
        ),
    )

    for rank, r in enumerate(sorted_tx, start=1):
        r["rank"] = rank

    batch = save_batch(filename, user_id, sorted_tx)
    return {"batch": batch}


@router.post("/upload")
async def upload_fraud_csv(
    file: UploadFile = File(...),
    user=Depends(require_permission("fraud:upload")),
):
    if not (file.filename and file.filename.lower().endswith(".csv")):
        raise HTTPException(status_code=400, detail="Only CSV documents are supported currently.")

    content = await file.read()
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="File too large (maximum 10 MB).")

    if not content or len(content.strip()) == 0:
        raise HTTPException(status_code=400, detail="The uploaded file is empty.")

    try:
        content_str = content.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="Could not decode CSV as UTF-8.")

    try:
        return await run_in_threadpool(_process_and_score_csv, file.filename, content_str, user["user_id"])
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/history")
def fraud_history(user=Depends(require_permission("fraud:read"))):
    from modules.fraud.storage import get_fraud_history
    return get_fraud_history()


@router.delete("/history")
def clear_history(user=Depends(require_permission("fraud:approve"))):
    from modules.fraud.storage import clear_fraud_history
    return clear_fraud_history()
