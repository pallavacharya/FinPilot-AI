"""AI AGENT LAYER (LANGGRAPH)  -  owner: Akshi Yadav

Replace the bodies of get_actions() and approve_action() with your LangGraph
agent loop. Keep the function names and return keys EXACTLY as below.
You can read Kritagy's output with:
    from modules.fraud import get_flagged_transactions
Every approval MUST be written to an audit log (who approved, what, when).
"""

# --- sample data (delete once the real agent is connected) ---
_ACTIONS = [
    {
        "id": "a9f12c",
        "title": "Draft alert: high-risk transaction TXN-88213",
        "body": "Anomaly score 0.94 exceeded the 0.85 threshold. Recommended action: notify account owner and hold settlement pending manual review.",
        "status": "pending_approval",
    },
    {
        "id": "b71de4",
        "title": "Log decision: TXN-88190 cleared after review",
        "body": "Analyst reviewed flagged transaction and marked as false positive. Action logged to audit trail with reviewer ID and timestamp.",
        "status": "executed",
    },
    {
        "id": "c3a908",
        "title": "Draft weekly summary report",
        "body": "Compiled forecast accuracy, fraud flags, and open Q&A threads into a summary for the business owner.",
        "status": "executed",
    },
]


def get_actions() -> list:
    """Return the agent's proposed / completed actions.

    Returns a list of:
        {
          "id": str,
          "title": str,                   # one-line summary
          "body": str,                    # explanation shown on the card
          "status": str,                  # "pending_approval" | "executed"
        }
    """
    return [dict(a) for a in _ACTIONS]


def approve_action(action_id: str, approved_by: str) -> dict:
    """A human approved an action: execute it and write the audit-log entry.

    Returns:
        {"action_id": str, "approved_by": str, "status": "executed"}
    """
    for a in _ACTIONS:
        if a["id"] == action_id:
            a["status"] = "executed"
    return {"action_id": action_id, "approved_by": approved_by, "status": "executed"}
