"""AI AGENT LAYER (LANGGRAPH) - FinPilot AI

Orchestrates deterministic report generation, approval-gated email delivery,
and business notifications for Fraud Alerts and Sales Outlook.
"""

import logging
import re
import threading
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, TypedDict

from langgraph.graph import END, START, StateGraph

from modules.agent import emailer, reports, store
from modules.forecasting import get_all_next_week, get_chart_data
from modules.fraud.storage import (
    get_all_batches_summary,
    get_batch_by_id,
    get_customer_batch_counts,
    get_latest_batch,
)

logger = logging.getLogger("finpilot.agent")

# Named constants per Section 3.3 and 6
FORECAST_DROP_RATIO = 0.70
FORECAST_DROP_MIN_AVG = 500.0
OVERDUE_HOURS = 4

_lazy_check_lock = threading.Lock()
_forecast_checked_once = False


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _is_valid_email(email: str) -> bool:
    if not email or len(email) > 254:
        return False
    return bool(re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email.strip()))


# -----------------------------------------------------------------------------
# LangGraph Workflow Definitions
# -----------------------------------------------------------------------------

class FraudState(TypedDict, total=False):
    batch_id: int
    batch: Optional[Dict[str, Any]]
    is_on_demand: bool
    suspicious_count: int
    report: Optional[Dict[str, Any]]
    action: Optional[Dict[str, Any]]
    repeat_offenders: List[Dict[str, Any]]
    error: Optional[str]


def _node_read_fraud_batch(state: FraudState) -> FraudState:
    batch_id = state.get("batch_id")
    if not batch_id:
        return {"error": "Missing batch_id"}
    batch = get_batch_by_id(batch_id)
    if not batch:
        return {"error": f"Batch {batch_id} not found"}
    return {"batch": batch}


def _node_analyse_fraud_batch(state: FraudState) -> FraudState:
    if state.get("error"):
        return state
    batch = state["batch"]
    flagged = [t for t in batch.get("transactions", []) if t.get("is_anomaly") or t.get("status") == "SUSPICIOUS"]
    suspicious_count = len(flagged)

    # Check for cross-upload repeat offenders
    cross_repeats = []
    if suspicious_count > 0:
        cust_counts = get_customer_batch_counts()
        seen_custs = set()
        for t in flagged:
            cid = str(t.get("customer_id", "")).strip()
            if cid and cid.lower() not in ("nan", "none", "unknown", "") and cid not in seen_custs:
                seen_custs.add(cid)
                c_batches = cust_counts.get(cid, 0)
                if c_batches > 1:
                    cross_repeats.append({"customer_id": cid, "uploads_count": c_batches})
        cross_repeats.sort(key=lambda x: x["uploads_count"], reverse=True)

    return {
        "suspicious_count": suspicious_count,
        "repeat_offenders": cross_repeats,
    }


def _router_fraud_decision(state: FraudState) -> str:
    if state.get("error"):
        return END
    if state.get("suspicious_count", 0) == 0:
        return "notify_clean"
    return "build_fraud_report"


def _node_notify_clean(state: FraudState) -> FraudState:
    batch = state["batch"]
    filename = batch.get("filename", "unknown.csv")
    total = batch.get("total_transactions", 0)
    store.create_notification(
        notif_type="info",
        title=f"Fraud check clean: {filename}",
        message=f"No suspicious transactions in {filename} ({total} transactions scanned).",
        action_id=None,
        report_id=None,
    )
    return state


def _node_build_fraud_report(state: FraudState) -> FraudState:
    batch = state["batch"]
    cust_counts = get_customer_batch_counts()
    report_dict = reports.build_fraud_report(batch, all_customer_batch_counts=cust_counts)
    saved_report = store.save_report(report_dict)
    store.write_audit_entry(
        event="report_generated",
        actor="agent",
        report_id=saved_report["id"],
        details={"kind": "fraud", "batch_id": batch.get("id"), "subject": saved_report["subject"]},
    )
    return {"report": saved_report}


def _node_propose_fraud_action(state: FraudState) -> FraudState:
    batch = state["batch"]
    report = state["report"]
    summary = report.get("summary", {})
    action_id = uuid.uuid4().hex[:6]
    action = {
        "id": action_id,
        "type": "fraud_report",
        "batch_id": batch.get("id"),
        "report_id": report["id"],
        "title": f"Draft alert: {summary.get('suspicious_count', 0)} suspicious transactions in {batch.get('filename')}",
        "body": (
            f"{summary.get('suspicious_count', 0)} of {summary.get('total_transactions', 0)} "
            f"transactions flagged ({summary.get('flag_rate_pct', 0.0):.1f}%). "
            f"Amount at risk: ₹{summary.get('amount_at_risk', 0.0):,.2f}. "
            "Needs approval before sending to business owner."
        ),
        "status": "pending_approval",
        "created_at": _now_iso(),
    }
    saved_action = store.save_action(action)
    store.write_audit_entry(
        event="action_proposed",
        actor="agent",
        action_id=saved_action["id"],
        report_id=report["id"],
        details={
            "type": "fraud_report",
            "batch_id": batch.get("id"),
            "suspicious_count": summary.get("suspicious_count", 0),
        },
    )
    return {"action": saved_action}


def _node_notify_fraud(state: FraudState) -> FraudState:
    batch = state["batch"]
    report = state["report"]
    action = state["action"]
    summary = report.get("summary", {})
    susp_count = summary.get("suspicious_count", 0)
    filename = batch.get("filename", "unknown.csv")

    store.create_notification(
        notif_type="fraud_alert",
        title=f"Fraud alert: {susp_count} suspicious transactions in {filename}",
        message=f"{susp_count} flagged transactions need review. Action {action['id']} is waiting for approval.",
        action_id=action["id"],
        report_id=report["id"],
    )

    # Cross-upload repeat offenders notification per upload
    cross_repeats = state.get("repeat_offenders", [])
    if cross_repeats:
        top5 = cross_repeats[:5]
        details_str = ", ".join(f"{r['customer_id']} ({r['uploads_count']} uploads)" for r in top5)
        store.create_notification(
            notif_type="repeat_offender",
            title=f"Repeat offenders flagged in {filename}",
            message=f"{len(cross_repeats)} repeat offender(s) detected across uploads: {details_str}.",
            action_id=action["id"],
            report_id=report["id"],
        )

    return state


# Build and compile Fraud Graph
fraud_builder = StateGraph(FraudState)
fraud_builder.add_node("read_batch", _node_read_fraud_batch)
fraud_builder.add_node("analyse_batch", _node_analyse_fraud_batch)
fraud_builder.add_node("notify_clean", _node_notify_clean)
fraud_builder.add_node("build_fraud_report", _node_build_fraud_report)
fraud_builder.add_node("propose_fraud_action", _node_propose_fraud_action)
fraud_builder.add_node("notify_fraud", _node_notify_fraud)

fraud_builder.add_edge(START, "read_batch")
fraud_builder.add_edge("read_batch", "analyse_batch")
fraud_builder.add_conditional_edges("analyse_batch", _router_fraud_decision)
fraud_builder.add_edge("notify_clean", END)
fraud_builder.add_edge("build_fraud_report", "propose_fraud_action")
fraud_builder.add_edge("propose_fraud_action", "notify_fraud")
fraud_builder.add_edge("notify_fraud", END)

fraud_graph = fraud_builder.compile()


# Sales Graph
class SalesState(TypedDict, total=False):
    report: Optional[Dict[str, Any]]
    action: Optional[Dict[str, Any]]
    error: Optional[str]


def _node_build_sales_report(state: SalesState) -> SalesState:
    try:
        report_dict = reports.build_sales_report()
        saved_report = store.save_report(report_dict)
        store.write_audit_entry(
            event="report_generated",
            actor="agent",
            report_id=saved_report["id"],
            details={"kind": "sales", "subject": saved_report["subject"]},
        )
        return {"report": saved_report}
    except Exception as e:
        logger.exception("Error building sales report: %s", e)
        return {"error": str(e)}


def _node_propose_sales_action(state: SalesState) -> SalesState:
    if state.get("error"):
        return state
    report = state["report"]
    summary = report.get("summary", {})
    action_id = uuid.uuid4().hex[:6]
    week_ending = summary.get("next_week_ending", "")
    next_week_sales = summary.get("next_week_total", 0.0)

    action = {
        "id": action_id,
        "type": "sales_report",
        "report_id": report["id"],
        "title": f"Draft sales outlook report for week ending {week_ending}",
        "body": (
            f"Sales forecast of ${next_week_sales:,.2f} compiled across 17 sub-categories. "
            "Needs approval before sending to business owner."
        ),
        "status": "pending_approval",
        "created_at": _now_iso(),
    }
    saved_action = store.save_action(action)
    store.write_audit_entry(
        event="action_proposed",
        actor="agent",
        action_id=saved_action["id"],
        report_id=report["id"],
        details={"type": "sales_report", "week_ending": week_ending},
    )
    return {"action": saved_action}


def _node_notify_sales(state: SalesState) -> SalesState:
    if state.get("error"):
        return state
    report = state["report"]
    action = state["action"]
    summary = report.get("summary", {})
    week_ending = summary.get("next_week_ending", "")

    store.create_notification(
        notif_type="info",
        title=f"Sales outlook report ready for review ({week_ending})",
        message=f"Sales forecast report generated. Action {action['id']} is waiting for approval.",
        action_id=action["id"],
        report_id=report["id"],
    )
    return state


sales_builder = StateGraph(SalesState)
sales_builder.add_node("build_sales_report", _node_build_sales_report)
sales_builder.add_node("propose_sales_action", _node_propose_sales_action)
sales_builder.add_node("notify_sales", _node_notify_sales)

sales_builder.add_edge(START, "build_sales_report")
sales_builder.add_edge("build_sales_report", "propose_sales_action")
sales_builder.add_edge("propose_sales_action", "notify_sales")
sales_builder.add_edge("notify_sales", END)

sales_graph = sales_builder.compile()


# -----------------------------------------------------------------------------
# Trigger & Periodic / Lazy Checks
# -----------------------------------------------------------------------------

def on_fraud_upload(batch_id: int) -> Dict[str, Any]:
    """Triggered immediately after a fraud CSV batch is saved.

    Guaranteed never to raise an unhandled exception so caller is unaffected.
    """
    try:
        # Check idempotency: one automatic action per (type, batch_id)
        if store.has_action_for_type_batch("fraud_report", batch_id):
            logger.info("Batch %s already has a fraud report action; skipping automatic trigger.", batch_id)
            return {"status": "skipped", "reason": "already_exists"}

        result_state = fraud_graph.invoke({"batch_id": batch_id, "is_on_demand": False})
        if result_state.get("error"):
            store.write_audit_entry(
                event="agent_error",
                actor="agent",
                details={"stage": "on_fraud_upload", "error": result_state["error"], "batch_id": batch_id},
            )
            return {"status": "error", "error": result_state["error"]}

        return {
            "status": "success",
            "action_id": result_state.get("action", {}).get("id"),
            "report_id": result_state.get("report", {}).get("id"),
        }
    except Exception as exc:
        logger.exception("Error running on_fraud_upload: %s", exc)
        store.write_audit_entry(
            event="agent_error",
            actor="agent",
            details={"stage": "on_fraud_upload", "error": str(exc), "batch_id": batch_id},
        )
        return {"status": "error", "error": str(exc)}


def check_forecast_drops() -> Optional[Dict[str, Any]]:
    """Checks for sub-categories where predicted sales <= 70% of 4-week avg and 4-week avg >= $500.

    Idempotent per forecast week_ending.
    """
    try:
        items = get_all_next_week()
        if not items:
            return None

        week_ending = items[0].get("week_ending", "")
        notif_title = f"Forecast drop warning ({week_ending})"

        # Check idempotency per week_ending
        if store.has_notification("forecast_drop", notif_title):
            return None

        dropped_items = []
        for it in items:
            sub = it["sub_category"]
            chart = get_chart_data(sub)
            actuals = [pt["sales"] for pt in chart.get("history", [])[-4:]]
            if len(actuals) == 4:
                avg4 = sum(actuals) / 4.0
                pred = it.get("predicted_sales", 0.0)
                if avg4 >= FORECAST_DROP_MIN_AVG and pred <= FORECAST_DROP_RATIO * avg4:
                    pct_drop = ((avg4 - pred) / avg4) * 100.0
                    dropped_items.append((sub, pct_drop))

        if not dropped_items:
            return None

        # Format items and percentage drops
        dropped_items.sort(key=lambda x: x[1], reverse=True)
        items_desc = ", ".join(f"{name} (-{pct:.0f}%)" for name, pct in dropped_items)
        msg = f"{len(dropped_items)} items projected to drop >30% below 4-week average: {items_desc}."

        notif = store.create_notification(
            notif_type="forecast_drop",
            title=notif_title,
            message=msg,
        )
        return notif
    except Exception as e:
        logger.exception("Error checking forecast drops: %s", e)
        return None


def check_overdue_actions() -> int:
    """Finds pending_approval actions older than OVERDUE_HOURS.

    Generates one reminder notification per overdue action.
    Sends reminder email if reminder_enabled is True and not already sent.
    """
    settings = store.get_settings()
    reminder_enabled = settings.get("reminder_enabled", False)
    owner_email = settings.get("owner_email", "").strip()

    actions = store.get_actions()
    now = datetime.now(timezone.utc)
    reminder_count = 0

    for a in actions:
        if a.get("status") != "pending_approval":
            continue

        created_str = a.get("created_at")
        if not created_str:
            continue
        try:
            created_dt = datetime.fromisoformat(created_str.replace("Z", "+00:00"))
        except Exception:
            continue

        elapsed_hours = (now - created_dt).total_seconds() / 3600.0
        if elapsed_hours >= OVERDUE_HOURS:
            notif_title = f"Approval reminder: {a.get('title')}"
            # Check if reminder notification already created for this action
            with store._get_db() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT 1 FROM notifications WHERE type = 'reminder' AND action_id = ? LIMIT 1;",
                    (a["id"],),
                )
                exists = cursor.fetchone() is not None

            if not exists:
                store.create_notification(
                    notif_type="reminder",
                    title=notif_title,
                    message=f"Action {a['id']} has been waiting for approval for {int(elapsed_hours)} hours.",
                    action_id=a["id"],
                    report_id=a.get("report_id"),
                )
                reminder_count += 1

                # Send reminder email if enabled
                if reminder_enabled and _is_valid_email(owner_email):
                    # Check audit log if reminder email already sent for this action
                    already_emailed = bool(store.get_audit_log(limit=50, event="reminder_sent"))
                    # Specifically check for action_id in audit log
                    sent_for_action = any(
                        entry.get("action_id") == a["id"]
                        for entry in store.get_audit_log(limit=100, event="reminder_sent")
                    )
                    if not sent_for_action:
                        rem_body = reports.build_reminder_email(a["title"], a["id"])
                        res = emailer.send_email(
                            to_email=owner_email,
                            subject=rem_body["subject"],
                            html_content=rem_body["html"],
                            text_content=rem_body["text"],
                        )
                        if res.get("success"):
                            store.write_audit_entry(
                                event="reminder_sent",
                                actor="agent",
                                action_id=a["id"],
                                report_id=a.get("report_id"),
                                details={"sent_to": owner_email, "mode": res.get("mode")},
                            )

    return reminder_count


def run_checks() -> Dict[str, Any]:
    """Runs missing-batch proposals, forecast drop check, and overdue check."""
    # 1. Forecast drop check
    check_forecast_drops()

    # 2. Overdue actions check
    overdue_count = check_overdue_actions()

    # 3. Missing batch proposals (if any batch with suspicious rows has no action)
    batches_summary = get_all_batches_summary()
    proposed_count = 0
    for b in batches_summary:
        bid = b["id"]
        if b.get("suspicious_count", 0) > 0 and not store.has_action_for_type_batch("fraud_report", bid):
            on_fraud_upload(bid)
            proposed_count += 1

    return {
        "status": "success",
        "overdue_reminders": overdue_count,
        "missing_proposals_created": proposed_count,
    }


def run_lazy_checks() -> None:
    """Run once on startup / first route call, and evaluate reminders on notifications call."""
    global _forecast_checked_once
    with _lazy_check_lock:
        if not _forecast_checked_once:
            check_forecast_drops()
            _forecast_checked_once = True
    check_overdue_actions()


# -----------------------------------------------------------------------------
# Public API Contracts
# -----------------------------------------------------------------------------

def get_actions() -> List[Dict[str, Any]]:
    """Return stored actions. Does NOT run any analysis."""
    actions = store.get_actions()
    # Compute waiting hours for pending actions
    now = datetime.now(timezone.utc)
    res = []
    for a in actions:
        item = dict(a)
        if item.get("status") == "pending_approval" and item.get("created_at"):
            try:
                c_dt = datetime.fromisoformat(item["created_at"].replace("Z", "+00:00"))
                hours = int((now - c_dt).total_seconds() / 3600.0)
                item["waiting_hours"] = hours
                item["is_overdue"] = hours >= OVERDUE_HOURS
            except Exception:
                item["waiting_hours"] = 0
                item["is_overdue"] = False
        else:
            item["waiting_hours"] = 0
            item["is_overdue"] = False
        res.append(item)
    return res


def approve_action(action_id: str, approved_by: str) -> Dict[str, Any]:
    """Approves and executes an action.

    Sends the stored report via emailer, marks executed only on success,
    creates a notification, and writes an audit log entry.
    """
    action = store.get_action_by_id(action_id)
    if not action:
        raise ValueError(f"Action '{action_id}' not found.")

    if action.get("status") in ("executed", "rejected"):
        raise ValueError(f"Action '{action_id}' is already {action.get('status')}.")

    settings = store.get_settings()
    owner_email = settings.get("owner_email", "").strip()
    if not _is_valid_email(owner_email):
        raise ValueError("Set the owner's email in Settings first.")

    report_id = action.get("report_id")
    if not report_id:
        raise ValueError(f"Action '{action_id}' has no associated report.")

    report = store.get_report_by_id(report_id)
    if not report:
        raise ValueError(f"Report '{report_id}' not found.")

    # Execute email send
    try:
        send_result = emailer.send_email(
            to_email=owner_email,
            subject=report["subject"],
            html_content=report["html"],
            text_content=report["text"],
            attachment_csv=report.get("attachment_csv"),
        )
    except Exception as exc:
        send_result = {"success": False, "error": str(exc)}

    now_iso = _now_iso()

    if send_result.get("success"):
        # Success path
        rep_status = "dry_run_saved" if send_result.get("mode") == "dry_run" else "sent"
        store.update_report(
            report_id,
            {
                "status": rep_status,
                "sent_to": owner_email,
                "sent_at": now_iso,
                "error": None,
            },
        )
        store.update_action(
            action_id,
            {
                "status": "executed",
                "approved_by": approved_by,
                "approved_at": now_iso,
                "execution_result": send_result.get("message", "Sent successfully"),
                "error": None,
            },
        )
        store.write_audit_entry(
            event="agent_action_approved_and_executed",
            actor=approved_by,
            action_id=action_id,
            report_id=report_id,
            details={
                "mode": send_result.get("mode"),
                "sent_to": owner_email,
                "message": send_result.get("message"),
            },
        )

        notif_msg = (
            f"Dry run: report saved, not emailed (to {owner_email})."
            if send_result.get("mode") == "dry_run"
            else f"Report emailed to {owner_email}."
        )
        store.create_notification(
            notif_type="report_sent",
            title=f"Report sent: {report['subject']}",
            message=notif_msg,
            action_id=action_id,
            report_id=report_id,
        )

        return {
            "action_id": action_id,
            "approved_by": approved_by,
            "status": "executed",
            "email": {
                "mode": send_result.get("mode"),
                "sent_to": owner_email,
                "report_id": report_id,
                "message": send_result.get("message"),
            },
        }
    else:
        # Failure path
        err_msg = send_result.get("error", "Unknown email sending error")
        store.update_action(
            action_id,
            {
                "status": "failed",
                "error": err_msg,
            },
        )
        store.update_report(
            report_id,
            {
                "status": "failed",
                "error": err_msg,
            },
        )
        store.write_audit_entry(
            event="send_failed",
            actor=approved_by,
            action_id=action_id,
            report_id=report_id,
            details={"error": err_msg, "to": owner_email},
        )
        raise RuntimeError(f"Email sending failed: {err_msg}")


def reject_action(action_id: str, rejected_by: str, reason: str = "") -> Dict[str, Any]:
    """Rejects an action, marks action and report as rejected, writes audit entry."""
    action = store.get_action_by_id(action_id)
    if not action:
        raise ValueError(f"Action '{action_id}' not found.")

    if action.get("status") in ("executed", "rejected"):
        raise ValueError(f"Action '{action_id}' is already {action.get('status')}.")

    now_iso = _now_iso()
    store.update_action(
        action_id,
        {
            "status": "rejected",
            "rejected_by": rejected_by,
            "rejected_at": now_iso,
            "rejection_reason": reason,
        },
    )

    report_id = action.get("report_id")
    if report_id:
        store.update_report(report_id, {"status": "rejected"})

    store.write_audit_entry(
        event="action_rejected",
        actor=rejected_by,
        action_id=action_id,
        report_id=report_id,
        details={"reason": reason},
    )

    return {
        "action_id": action_id,
        "rejected_by": rejected_by,
        "status": "rejected",
        "reason": reason,
    }


def generate_report(kind: str, scope: str = "newest", batch_id: Optional[int] = None) -> Dict[str, Any]:
    """Creates an on-demand draft report plus a pending approval action."""
    if kind == "fraud":
        if scope == "batch" and batch_id:
            batch = get_batch_by_id(batch_id)
            if not batch:
                raise ValueError(f"Batch {batch_id} not found.")
        elif scope == "all":
            all_summary = get_all_batches_summary()
            if not all_summary:
                raise ValueError("No fraud batches uploaded yet.")
            # For scope="all", build combined batch representation
            combined_txs = []
            for b in all_summary:
                b_full = get_batch_by_id(b["id"])
                if b_full and b_full.get("transactions"):
                    combined_txs.extend(b_full["transactions"])
            batch = {
                "id": None,
                "filename": f"All Uploads ({len(all_summary)} files)",
                "total_transactions": len(combined_txs),
                "transactions": combined_txs,
            }
        else:  # newest
            batch = get_latest_batch()
            if not batch:
                raise ValueError("No fraud batches uploaded yet.")

        # On-demand reports are never de-duplicated
        cust_counts = get_customer_batch_counts()
        rep_dict = reports.build_fraud_report(batch, all_customer_batch_counts=cust_counts)
        saved_report = store.save_report(rep_dict)
        summary = saved_report.get("summary", {})

        action_id = uuid.uuid4().hex[:6]
        action = {
            "id": action_id,
            "type": "fraud_report",
            "batch_id": batch.get("id"),
            "report_id": saved_report["id"],
            "title": f"Draft alert: {summary.get('suspicious_count', 0)} suspicious transactions in {batch.get('filename')}",
            "body": (
                f"{summary.get('suspicious_count', 0)} of {summary.get('total_transactions', 0)} "
                f"transactions flagged ({summary.get('flag_rate_pct', 0.0):.1f}%). "
                f"Amount at risk: ₹{summary.get('amount_at_risk', 0.0):,.2f}. "
                "Needs approval before sending to business owner."
            ),
            "status": "pending_approval",
            "created_at": _now_iso(),
        }
        saved_action = store.save_action(action)

        store.write_audit_entry(
            event="report_generated",
            actor="agent",
            report_id=saved_report["id"],
            details={"kind": "fraud", "scope": scope, "batch_id": batch.get("id")},
        )
        store.write_audit_entry(
            event="action_proposed",
            actor="agent",
            action_id=saved_action["id"],
            report_id=saved_report["id"],
            details={"type": "fraud_report", "scope": scope},
        )

        store.create_notification(
            notif_type="fraud_alert",
            title=f"Fraud report generated: {batch.get('filename')}",
            message=f"{summary.get('suspicious_count', 0)} flagged transactions. Action {saved_action['id']} created.",
            action_id=saved_action["id"],
            report_id=saved_report["id"],
        )

        return {
            "report": saved_report,
            "action": saved_action,
        }

    elif kind == "sales":
        res_state = sales_graph.invoke({})
        if res_state.get("error"):
            raise RuntimeError(f"Error generating sales report: {res_state['error']}")
        return {
            "report": res_state.get("report"),
            "action": res_state.get("action"),
        }

    else:
        raise ValueError(f"Unknown report kind: '{kind}'. Expected 'fraud' or 'sales'.")
