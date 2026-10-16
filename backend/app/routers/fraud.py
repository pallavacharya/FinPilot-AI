from fastapi import APIRouter, Depends
from pydantic import BaseModel
from app.auth_utils import require_permission
from modules.fraud import get_flagged_transactions

router = APIRouter()

# Human review decisions made in the dashboard, layered on top of the model output.
# (In-memory for now; moves to the database later.)
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
