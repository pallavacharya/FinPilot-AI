import re
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import HTMLResponse, PlainTextResponse
from pydantic import BaseModel, Field

from app.auth_utils import require_permission
from modules import agent
from modules.agent import emailer, store

router = APIRouter()


# -----------------------------------------------------------------------------
# Actions Endpoints
# -----------------------------------------------------------------------------

@router.get("/actions")
def list_actions(user=Depends(require_permission("agent:approve"))):
    agent.run_lazy_checks()
    return {"actions": agent.get_actions()}


class ApproveRequest(BaseModel):
    action_id: str
    recipient_email: Optional[str] = None


@router.post("/actions/approve")
def approve(payload: ApproveRequest, user=Depends(require_permission("agent:approve"))):
    try:
        return agent.approve_action(payload.action_id, user["user_id"], recipient_email=payload.recipient_email)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class RejectRequest(BaseModel):
    action_id: str
    reason: Optional[str] = ""


@router.post("/actions/reject")
def reject(payload: RejectRequest, user=Depends(require_permission("agent:approve"))):
    try:
        return agent.reject_action(payload.action_id, user["user_id"], payload.reason or "")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/run-checks")
def run_all_checks(user=Depends(require_permission("agent:approve"))):
    try:
        return agent.run_checks()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Check execution failed: {e}")


# -----------------------------------------------------------------------------
# Notifications Endpoints
# -----------------------------------------------------------------------------

@router.get("/notifications")
def list_notifications(
    unread_only: bool = Query(False),
    limit: int = Query(200, ge=1, le=500),
    user=Depends(require_permission("agent:approve")),
):
    agent.run_lazy_checks()
    return {"notifications": store.get_notifications(unread_only=unread_only, limit=limit)}


@router.get("/notifications/unread-count")
def unread_count(user=Depends(require_permission("agent:approve"))):
    return {"count": store.get_unread_notification_count()}


class MarkReadRequest(BaseModel):
    ids: Optional[List[int]] = None
    all: Optional[bool] = False


@router.post("/notifications/read")
def mark_read(payload: MarkReadRequest, user=Depends(require_permission("agent:approve"))):
    updated = store.mark_notifications_read(ids=payload.ids, all_unread=bool(payload.all))
    return {"updated": updated}


# -----------------------------------------------------------------------------
# Reports Endpoints
# -----------------------------------------------------------------------------

@router.get("/reports")
def list_reports(
    kind: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=200),
    user=Depends(require_permission("agent:approve")),
):
    return {"reports": store.get_reports_list(kind=kind, limit=limit)}


@router.get("/reports/{report_id}")
def get_report(report_id: str, user=Depends(require_permission("agent:approve"))):
    report = store.get_report_by_id(report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    return {"report": report}


@router.get("/reports/{report_id}/download-html")
def download_report_html(report_id: str, user=Depends(require_permission("agent:approve"))):
    report = store.get_report_by_id(report_id)
    if not report or not report.get("html"):
        raise HTTPException(status_code=404, detail="Report HTML not found")
    filename = f"FinPilot_Report_{report_id[:8]}.html"
    return HTMLResponse(
        content=report["html"],
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/reports/{report_id}/download-csv")
def download_report_csv(report_id: str, user=Depends(require_permission("agent:approve"))):
    report = store.get_report_by_id(report_id)
    if not report or not report.get("attachment_csv"):
        raise HTTPException(status_code=404, detail="No CSV attachment found for this report")
    filename = f"FinPilot_Report_Data_{report_id[:8]}.csv"
    return PlainTextResponse(
        content=report["attachment_csv"],
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


class GenerateReportRequest(BaseModel):
    kind: str = Field(..., description="'fraud' or 'sales'")
    scope: Optional[str] = Field("newest", description="'newest', 'all', or 'batch'")
    batch_id: Optional[int] = None


@router.post("/reports/generate")
def generate_report_endpoint(
    payload: GenerateReportRequest,
    user=Depends(require_permission("agent:approve")),
):
    if payload.kind not in ("fraud", "sales"):
        raise HTTPException(status_code=400, detail="kind must be 'fraud' or 'sales'")
    try:
        return agent.generate_report(
            kind=payload.kind,
            scope=payload.scope or "newest",
            batch_id=payload.batch_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# -----------------------------------------------------------------------------
# Audit Log Endpoints
# -----------------------------------------------------------------------------

@router.get("/audit")
def get_audit(
    limit: int = Query(100, ge=1, le=500),
    event: Optional[str] = Query(None),
    user=Depends(require_permission("agent:approve")),
):
    return {"entries": store.get_audit_log(limit=limit, event=event)}


# -----------------------------------------------------------------------------
# Settings Endpoints
# -----------------------------------------------------------------------------

@router.get("/settings")
def get_agent_settings(user=Depends(require_permission("agent:approve"))):
    return store.get_settings()


class UpdateSettingsRequest(BaseModel):
    owner_email: Optional[str] = None
    reminder_enabled: Optional[bool] = None
    reminder_hours: Optional[int] = None


@router.put("/settings")
def update_agent_settings(
    payload: UpdateSettingsRequest,
    user=Depends(require_permission("settings:manage")),
):
    if payload.owner_email is not None and payload.owner_email.strip():
        email = payload.owner_email.strip()
        if len(email) > 254 or not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email):
            raise HTTPException(status_code=400, detail="Invalid email address format.")

    res = store.update_settings(
        owner_email=payload.owner_email,
        reminder_enabled=payload.reminder_enabled,
        reminder_hours=payload.reminder_hours,
    )

    store.write_audit_entry(
        event="settings_changed",
        actor=user["user_id"],
        details={
            "owner_email_set": bool(payload.owner_email),
            "reminder_enabled": payload.reminder_enabled,
            "reminder_hours": payload.reminder_hours,
        },
    )
    return res


@router.post("/settings/test-email")
def test_email_endpoint(user=Depends(require_permission("settings:manage"))):
    settings = store.get_settings()
    owner_email = settings.get("owner_email", "").strip()
    if not owner_email or not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", owner_email):
        raise HTTPException(status_code=400, detail="Set a valid owner email in Settings first.")

    try:
        res = emailer.send_test_email(owner_email)
        store.write_audit_entry(
            event="test_email_sent",
            actor=user["user_id"],
            details={"sent_to": owner_email, "mode": res.get("mode")},
        )
        return res
    except RuntimeError as e:
        msg = str(e)
        if "wait" in msg.lower() and "second" in msg.lower():
            raise HTTPException(status_code=429, detail=msg)
        raise HTTPException(status_code=502, detail=msg)
