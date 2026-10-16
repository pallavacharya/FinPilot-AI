from fastapi import APIRouter, Depends
from pydantic import BaseModel
from app.auth_utils import require_permission
from modules.agent import get_actions, approve_action

router = APIRouter()


@router.get("/actions")
def list_actions(user=Depends(require_permission("agent:approve"))):
    return {"actions": get_actions()}


class ApproveRequest(BaseModel):
    action_id: str


@router.post("/actions/approve")
def approve(payload: ApproveRequest, user=Depends(require_permission("agent:approve"))):
    return approve_action(payload.action_id, user["user_id"])
