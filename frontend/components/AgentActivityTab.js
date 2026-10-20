import React, { useState, useEffect } from "react";
import {
  getAgentActions,
  getAuditLog,
  getAgentSettings,
  updateAgentSettings,
  sendTestEmail,
  runAgentChecks,
  rejectAction,
  generateReport,
} from "../lib/api";
import {
  IconCheck,
  IconClock,
  IconRefresh,
  IconGear,
  IconMail,
  IconX,
} from "./icons";

function formatTimestamp(isoString) {
  if (!isoString) return "";
  try {
    const d = new Date(isoString);
    return d.toLocaleString("en-US", {
      month: "short",
      day: "numeric",
      year: "numeric",
      hour: "numeric",
      minute: "2-digit",
    });
  } catch (e) {
    return isoString;
  }
}

function formatEventName(event) {
  switch (event) {
    case "action_proposed":
      return "Action Proposed";
    case "report_generated":
      return "Report Generated";
    case "agent_action_approved_and_executed":
      return "Approved & Dispatched";
    case "send_failed":
      return "Dispatch Failed";
    case "action_rejected":
      return "Action Rejected";
    case "settings_changed":
      return "Settings Updated";
    case "test_email_sent":
      return "Test Email Sent";
    case "reminder_sent":
      return "Reminder Sent";
    case "agent_error":
      return "Agent Error";
    default:
      return event.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
  }
}

export default function AgentActivityTab({
  session,
  onOpenApproval,
  onRefreshCount,
  onNavigateTab,
}) {
  const [subtab, setSubtab] = useState("actions"); // 'actions' | 'audit' | 'settings'

  // Actions subtab state
  const [actions, setActions] = useState([]);
  const [actionsFilter, setActionsFilter] = useState("all"); // 'all' | 'pending' | 'done'
  const [loadingActions, setLoadingActions] = useState(true);
  const [runningChecks, setRunningChecks] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [showGenMenu, setShowGenMenu] = useState(false);

  // Audit subtab state
  const [auditLog, setAuditLog] = useState([]);
  const [auditEventFilter, setAuditEventFilter] = useState("");
  const [auditLimit, setAuditLimit] = useState(100);
  const [loadingAudit, setLoadingAudit] = useState(false);

  // Settings subtab state
  const [settings, setSettings] = useState(null);
  const [ownerEmailInput, setOwnerEmailInput] = useState("");
  const [reminderEnabled, setReminderEnabled] = useState(false);
  const [reminderHours, setReminderHours] = useState(4);
  const [savingSettings, setSavingSettings] = useState(false);
  const [settingsSavedMsg, setSettingsSavedMsg] = useState(null);
  const [settingsErrorMsg, setSettingsErrorMsg] = useState(null);
  const [sendingTest, setSendingTest] = useState(false);
  const [testResult, setTestResult] = useState(null);

  const isOwner = session?.role === "owner";

  // Load actions
  function loadActions() {
    setLoadingActions(true);
    getAgentActions()
      .then((res) => {
        setActions(res.actions || []);
        setLoadingActions(false);
      })
      .catch(() => {
        setActions([]);
        setLoadingActions(false);
      });
  }

  // Load audit log
  function loadAudit(limit = auditLimit, event = auditEventFilter) {
    setLoadingAudit(true);
    getAuditLog(limit, event || null)
      .then((res) => {
        setAuditLog(res.entries || []);
        setLoadingAudit(false);
      })
      .catch(() => {
        setAuditLog([]);
        setLoadingAudit(false);
      });
  }

  // Load settings
  function loadSettings() {
    getAgentSettings()
      .then((res) => {
        setSettings(res);
        setOwnerEmailInput(res.owner_email || "");
        setReminderEnabled(Boolean(res.reminder_enabled));
        setReminderHours(res.reminder_hours || 4);
      })
      .catch(() => {});
  }

  useEffect(() => {
    loadActions();
    loadSettings();
  }, []);

  useEffect(() => {
    if (subtab === "audit") {
      loadAudit(auditLimit, auditEventFilter);
    } else if (subtab === "settings") {
      loadSettings();
    } else {
      loadActions();
    }
  }, [subtab]);

  async function handleRunChecks() {
    setRunningChecks(true);
    try {
      await runAgentChecks();
      loadActions();
      if (onRefreshCount) onRefreshCount();
    } catch (e) {
      console.error("Run checks failed", e);
    } finally {
      setRunningChecks(false);
    }
  }

  async function handleGenerate(kind, scope = "newest") {
    setGenerating(true);
    setShowGenMenu(false);
    try {
      const res = await generateReport(kind, scope);
      loadActions();
      if (onRefreshCount) onRefreshCount();
      if (res.action && onOpenApproval) {
        onOpenApproval(res.action);
      }
    } catch (err) {
      alert(err.message || "Failed to generate report.");
    } finally {
      setGenerating(false);
    }
  }

  async function handleReject(actionId) {
    const reason = prompt("Enter an optional rejection reason:") || "";
    try {
      await rejectAction(actionId, reason);
      loadActions();
      if (onRefreshCount) onRefreshCount();
    } catch (e) {
      alert(e.message || "Rejection failed");
    }
  }

  async function handleSaveSettings(e) {
    if (e) e.preventDefault();
    if (!isOwner) return;
    setSavingSettings(true);
    setSettingsSavedMsg(null);
    setSettingsErrorMsg(null);
    try {
      const res = await updateAgentSettings({
        owner_email: ownerEmailInput.trim(),
        reminder_enabled: reminderEnabled,
        reminder_hours: parseInt(reminderHours, 10) || 4,
      });
      setSettings(res);
      setSettingsSavedMsg("Settings saved successfully.");
      setTimeout(() => setSettingsSavedMsg(null), 3000);
    } catch (err) {
      setSettingsErrorMsg(err.message || "Failed to update settings.");
    } finally {
      setSavingSettings(false);
    }
  }

  async function handleSendTestEmail() {
    setSendingTest(true);
    setTestResult(null);
    try {
      const res = await sendTestEmail();
      setTestResult({ success: true, message: res.message || "Test email sent successfully." });
    } catch (err) {
      setTestResult({ success: false, message: err.message || "Failed to send test email." });
    } finally {
      setSendingTest(false);
    }
  }

  const filteredActions = actions.filter((a) => {
    if (actionsFilter === "pending") return a.status === "pending_approval" || a.status === "failed";
    if (actionsFilter === "done") return a.status === "executed" || a.status === "rejected";
    return true;
  });

  return (
    <div>
      {/* Top Header */}
      <div className="topbar">
        <div>
          <h2>Agent Activity</h2>
          <div className="sub">LangGraph decision loop &middot; served from /api/v1/agent</div>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
          <span className="pill">Audit trail: 100% coverage</span>
        </div>
      </div>

      {/* Subtab Navigation */}
      <div style={{ display: "flex", gap: "10px", marginBottom: "22px", borderBottom: "1px solid var(--border)", paddingBottom: "12px" }}>
        <button
          type="button"
          className={`btn ${subtab === "actions" ? "primary" : ""}`}
          onClick={() => setSubtab("actions")}
          style={{ width: "auto", fontSize: "13px", padding: "8px 16px" }}
        >
          Proposed Actions ({actions.filter((a) => a.status === "pending_approval").length} pending)
        </button>
        <button
          type="button"
          className={`btn ${subtab === "audit" ? "primary" : ""}`}
          onClick={() => setSubtab("audit")}
          style={{ width: "auto", fontSize: "13px", padding: "8px 16px" }}
        >
          Audit Log
        </button>
        <button
          type="button"
          className={`btn ${subtab === "settings" ? "primary" : ""}`}
          onClick={() => setSubtab("settings")}
          style={{ width: "auto", fontSize: "13px", padding: "8px 16px", display: "flex", alignItems: "center", gap: "6px" }}
        >
          <IconGear size={16} /> Agent Settings
        </button>
      </div>

      {/* SUBTAB 1: ACTIONS */}
      {subtab === "actions" && (
        <div>
          {/* Action Bar */}
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "16px", flexWrap: "wrap", gap: "12px" }}>
            <div style={{ display: "flex", gap: "8px" }}>
              <button
                type="button"
                className={`btn ${actionsFilter === "all" ? "primary" : ""}`}
                onClick={() => setActionsFilter("all")}
                style={{ padding: "6px 14px", fontSize: "12px", width: "auto" }}
              >
                All ({actions.length})
              </button>
              <button
                type="button"
                className={`btn ${actionsFilter === "pending" ? "primary" : ""}`}
                onClick={() => setActionsFilter("pending")}
                style={{ padding: "6px 14px", fontSize: "12px", width: "auto" }}
              >
                Pending ({actions.filter((a) => a.status === "pending_approval" || a.status === "failed").length})
              </button>
              <button
                type="button"
                className={`btn ${actionsFilter === "done" ? "primary" : ""}`}
                onClick={() => setActionsFilter("done")}
                style={{ padding: "6px 14px", fontSize: "12px", width: "auto" }}
              >
                Done ({actions.filter((a) => a.status === "executed" || a.status === "rejected").length})
              </button>
            </div>

            <div style={{ display: "flex", gap: "10px", alignItems: "center", position: "relative" }}>
              <button
                type="button"
                className="btn"
                onClick={handleRunChecks}
                disabled={runningChecks}
                style={{ fontSize: "12px", padding: "6px 12px", display: "flex", alignItems: "center", gap: "6px" }}
              >
                <IconRefresh size={14} /> {runningChecks ? "Checking..." : "Run checks now"}
              </button>

              <div style={{ position: "relative" }}>
                <button
                  type="button"
                  className="btn"
                  onClick={() => setShowGenMenu((prev) => !prev)}
                  style={{ fontSize: "12px", padding: "6px 12px" }}
                >
                  + Generate report now &darr;
                </button>
                {showGenMenu && (
                  <div
                    style={{
                      position: "absolute",
                      right: 0,
                      top: "calc(100% + 6px)",
                      background: "var(--panel-2)",
                      border: "1px solid var(--border)",
                      borderRadius: "8px",
                      boxShadow: "0 8px 24px rgba(0,0,0,0.4)",
                      zIndex: 100,
                      width: "220px",
                      overflow: "hidden",
                    }}
                  >
                    <button
                      type="button"
                      onClick={() => handleGenerate("sales")}
                      style={{
                        width: "100%",
                        padding: "10px 14px",
                        textAlign: "left",
                        background: "none",
                        border: "none",
                        color: "var(--text)",
                        fontSize: "12.5px",
                        cursor: "pointer",
                        borderBottom: "1px solid var(--border)",
                      }}
                      onMouseEnter={(e) => (e.target.style.background = "var(--panel)")}
                      onMouseLeave={(e) => (e.target.style.background = "none")}
                    >
                      Sales Outlook Report
                    </button>
                    <button
                      type="button"
                      onClick={() => handleGenerate("fraud", "newest")}
                      style={{
                        width: "100%",
                        padding: "10px 14px",
                        textAlign: "left",
                        background: "none",
                        border: "none",
                        color: "var(--text)",
                        fontSize: "12.5px",
                        cursor: "pointer",
                        borderBottom: "1px solid var(--border)",
                      }}
                      onMouseEnter={(e) => (e.target.style.background = "var(--panel)")}
                      onMouseLeave={(e) => (e.target.style.background = "none")}
                    >
                      Fraud Report (Newest upload)
                    </button>
                    <button
                      type="button"
                      onClick={() => handleGenerate("fraud", "all")}
                      style={{
                        width: "100%",
                        padding: "10px 14px",
                        textAlign: "left",
                        background: "none",
                        border: "none",
                        color: "var(--text)",
                        fontSize: "12.5px",
                        cursor: "pointer",
                      }}
                      onMouseEnter={(e) => (e.target.style.background = "var(--panel)")}
                      onMouseLeave={(e) => (e.target.style.background = "none")}
                    >
                      Fraud Report (All uploads)
                    </button>
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* Cards List */}
          {loadingActions ? (
            <div className="loading" style={{ padding: "40px", textAlign: "center" }}>
              Loading agent actions...
            </div>
          ) : filteredActions.length === 0 ? (
            <div className="card fraud-empty-card">
              <h3 style={{ margin: "0 0 8px 0", fontSize: "16px", color: "var(--text)" }}>
                No actions found
              </h3>
              <p className="empty-subtext">
                All proposed actions have been executed or dismissed.
              </p>
            </div>
          ) : (
            filteredActions.map((a) => {
              const isOverdue = a.is_overdue || (a.waiting_hours >= 4 && a.status === "pending_approval");
              const isExecuted = a.status === "executed";
              const isFailed = a.status === "failed";
              const isRejected = a.status === "rejected";

              return (
                <div
                  key={a.id}
                  className={`agentcard ${isExecuted ? "approved" : ""}`}
                  style={{
                    background: "var(--panel)",
                    border: "1px solid var(--border)",
                    borderRadius: "12px",
                    padding: "18px 20px",
                    marginBottom: "14px",
                    position: "relative",
                  }}
                >
                  {/* Top Bar with chips */}
                  <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "10px", flexWrap: "wrap", gap: "8px" }}>
                    <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                      {a.type && (
                        <span
                          style={{
                            fontFamily: "var(--font-mono)",
                            fontSize: "10.5px",
                            fontWeight: 700,
                            padding: "2px 8px",
                            borderRadius: "4px",
                            background: a.type === "fraud_report" ? "rgba(229,89,95,0.12)" : "rgba(62,207,142,0.12)",
                            color: a.type === "fraud_report" ? "var(--red)" : "var(--accent)",
                            border: a.type === "fraud_report" ? "1px solid rgba(229,89,95,0.3)" : "1px solid rgba(62,207,142,0.3)",
                          }}
                        >
                          {a.type === "fraud_report" ? "FRAUD ALERT" : "SALES REPORT"}
                        </span>
                      )}

                      {/* Overdue Waiting Badge */}
                      {isOverdue && (
                        <span
                          style={{
                            fontFamily: "var(--font-mono)",
                            fontSize: "10.5px",
                            fontWeight: 700,
                            padding: "2px 8px",
                            borderRadius: "4px",
                            background: "rgba(240,168,87,0.15)",
                            color: "var(--amber)",
                            border: "1px solid rgba(240,168,87,0.35)",
                            display: "inline-flex",
                            alignItems: "center",
                            gap: "4px",
                          }}
                        >
                          <IconClock size={12} /> Waiting {a.waiting_hours} h
                        </span>
                      )}
                    </div>

                    <span style={{ fontSize: "11.5px", color: "var(--faint)" }}>
                      {formatTimestamp(a.created_at)}
                    </span>
                  </div>

                  {/* Title & Body */}
                  <h4 style={{ margin: "0 0 6px 0", fontSize: "15px", fontWeight: 700, color: "var(--text)" }}>
                    {a.title}
                  </h4>
                  <p style={{ margin: "0 0 16px 0", fontSize: "13.5px", color: "var(--muted)", lineHeight: 1.5 }}>
                    {a.body}
                  </p>

                  {/* Action State / Buttons */}
                  <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: "10px", borderTop: "1px solid var(--border)", paddingTop: "14px" }}>
                    <div>
                      {isExecuted ? (
                        <div style={{ fontSize: "12px", color: "var(--accent)", display: "flex", alignItems: "center", gap: "6px" }}>
                          <span className="dot" style={{ background: "var(--accent)" }}></span>
                          <span>
                            Approved by <strong>{a.approved_by || "analyst"}</strong> on {formatTimestamp(a.approved_at || a.created_at)}. {a.execution_result}
                          </span>
                        </div>
                      ) : isFailed ? (
                        <div style={{ fontSize: "12px", color: "var(--red)" }}>
                          Send failed: {a.error || "Mail transmission error"}
                        </div>
                      ) : isRejected ? (
                        <div style={{ fontSize: "12px", color: "var(--muted)" }}>
                          Rejected by <strong>{a.rejected_by || "analyst"}</strong> {a.rejection_reason ? `(${a.rejection_reason})` : ""}.
                        </div>
                      ) : (
                        <div style={{ fontSize: "12px", color: "var(--faint)" }}>
                          Requires approval before delivery to business owner
                        </div>
                      )}
                    </div>

                    <div style={{ display: "flex", gap: "8px" }}>
                      {isExecuted && a.report_id && (
                        <button
                          type="button"
                          className="btn"
                          onClick={() => onNavigateTab && onNavigateTab("reports")}
                          style={{ padding: "6px 14px", fontSize: "12px" }}
                        >
                          View report
                        </button>
                      )}

                      {isFailed && (
                        <button
                          type="button"
                          className="btn danger-btn"
                          onClick={() => onOpenApproval && onOpenApproval(a)}
                          style={{ padding: "6px 14px", fontSize: "12px" }}
                        >
                          Retry dispatch
                        </button>
                      )}

                      {!isExecuted && !isRejected && !isFailed && (
                        <>
                          <button
                            type="button"
                            className="btn"
                            onClick={() => handleReject(a.id)}
                            style={{ padding: "6px 12px", fontSize: "12px", color: "var(--red)", borderColor: "rgba(229,89,95,0.3)" }}
                          >
                            Reject
                          </button>
                          <button
                            type="button"
                            className="btn primary"
                            onClick={() => onOpenApproval && onOpenApproval(a)}
                            style={{ padding: "6px 16px", fontSize: "12px", width: "auto" }}
                          >
                            Review &amp; approve
                          </button>
                        </>
                      )}
                    </div>
                  </div>

                  <div className="audit" style={{ marginTop: "12px", fontSize: "11px", color: "var(--faint)", fontFamily: "var(--font-mono)" }}>
                    action_id: {a.id} &middot; actor: agent.langgraph &middot; gate: human_approval_required
                  </div>
                </div>
              );
            })
          )}
        </div>
      )}

      {/* SUBTAB 2: AUDIT LOG */}
      {subtab === "audit" && (
        <div>
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "16px" }}>
            <div style={{ fontSize: "13px", color: "var(--muted)" }}>
              Immutable append-only trail stored at <code>backend/data/audit_log.jsonl</code>
            </div>
            <div style={{ display: "flex", gap: "8px", alignItems: "center" }}>
              <span style={{ fontSize: "12px", color: "var(--faint)" }}>Filter event:</span>
              <select
                className="field"
                value={auditEventFilter}
                onChange={(e) => {
                  setAuditEventFilter(e.target.value);
                  loadAudit(auditLimit, e.target.value);
                }}
                style={{ width: "auto", margin: 0, padding: "6px 10px", fontSize: "12px" }}
              >
                <option value="">All events</option>
                <option value="action_proposed">action_proposed</option>
                <option value="report_generated">report_generated</option>
                <option value="agent_action_approved_and_executed">agent_action_approved_and_executed</option>
                <option value="send_failed">send_failed</option>
                <option value="action_rejected">action_rejected</option>
                <option value="settings_changed">settings_changed</option>
                <option value="test_email_sent">test_email_sent</option>
                <option value="reminder_sent">reminder_sent</option>
                <option value="agent_error">agent_error</option>
              </select>
            </div>
          </div>

          <div className="card" style={{ padding: 0, overflow: "hidden", border: "1px solid var(--border)" }}>
            <div className="table-responsive">
              <table style={{ width: "100%", borderCollapse: "collapse", textAlign: "left", fontSize: "12.5px" }}>
                <thead>
                  <tr style={{ background: "var(--panel-2)", borderBottom: "1px solid var(--border)", color: "var(--faint)" }}>
                    <th style={{ padding: "10px 14px", fontWeight: 600 }}>Timestamp</th>
                    <th style={{ padding: "10px 14px", fontWeight: 600 }}>Event</th>
                    <th style={{ padding: "10px 14px", fontWeight: 600 }}>Actor</th>
                    <th style={{ padding: "10px 14px", fontWeight: 600 }}>IDs</th>
                    <th style={{ padding: "10px 14px", fontWeight: 600 }}>Details</th>
                  </tr>
                </thead>
                <tbody>
                  {auditLog.length === 0 ? (
                    <tr>
                      <td colSpan={5} style={{ padding: "24px", textAlign: "center", color: "var(--muted)" }}>
                        {loadingAudit ? "Loading audit log entries..." : "No audit entries recorded."}
                      </td>
                    </tr>
                  ) : (
                    auditLog.map((entry, idx) => (
                      <tr key={idx} style={{ borderBottom: "1px solid var(--border)" }}>
                        <td style={{ padding: "10px 14px", fontFamily: "var(--font-mono)", color: "var(--muted)", whiteSpace: "nowrap" }}>
                          {formatTimestamp(entry.timestamp)}
                        </td>
                        <td style={{ padding: "10px 14px", fontWeight: 600, color: "var(--text)" }}>
                          {formatEventName(entry.event)}
                        </td>
                        <td style={{ padding: "10px 14px", color: "var(--muted)" }}>
                          {entry.actor}
                        </td>
                        <td style={{ padding: "10px 14px", fontFamily: "var(--font-mono)", fontSize: "11px", color: "var(--faint)" }}>
                          {entry.action_id && <span>act:{entry.action_id} </span>}
                          {entry.report_id && <span>rep:{entry.report_id}</span>}
                          {!entry.action_id && !entry.report_id && <span>&mdash;</span>}
                        </td>
                        <td style={{ padding: "10px 14px", color: "var(--muted)", fontSize: "11.5px" }}>
                          {entry.details ? JSON.stringify(entry.details) : ""}
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>

            {auditLog.length >= auditLimit && (
              <div style={{ padding: "12px", textAlign: "center", borderTop: "1px solid var(--border)", background: "var(--panel)" }}>
                <button
                  type="button"
                  className="btn"
                  onClick={() => {
                    const next = auditLimit + 100;
                    setAuditLimit(next);
                    loadAudit(next, auditEventFilter);
                  }}
                  style={{ fontSize: "12px", padding: "6px 16px" }}
                >
                  Load more audit entries
                </button>
              </div>
            )}
          </div>
        </div>
      )}

      {/* SUBTAB 3: SETTINGS */}
      {subtab === "settings" && (
        <div style={{ maxWidth: "680px" }}>
          <div className="card" style={{ padding: "24px", border: "1px solid var(--border)", borderRadius: "12px" }}>
            <h3 style={{ margin: "0 0 4px 0", fontSize: "16px", fontWeight: 700, color: "var(--text)" }}>
              Email Dispatch &amp; Notification Settings
            </h3>
            <p style={{ margin: "0 0 20px 0", fontSize: "13px", color: "var(--muted)" }}>
              Configure approval recipient and automated reminder thresholds.
            </p>

            {/* Email Mode Status Line */}
            <div
              style={{
                padding: "12px 16px",
                background: "var(--panel-2)",
                border: "1px solid var(--border)",
                borderRadius: "8px",
                marginBottom: "20px",
              }}
            >
              <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "6px" }}>
                <span style={{ fontSize: "12.5px", fontWeight: 600, color: "var(--text)" }}>
                  Email Delivery Mode:
                </span>
                <span
                  style={{
                    fontFamily: "var(--font-mono)",
                    fontSize: "11px",
                    fontWeight: 700,
                    padding: "2px 8px",
                    borderRadius: "4px",
                    background: settings?.email?.mode === "smtp" ? "rgba(240,168,87,0.15)" : "rgba(62,207,142,0.15)",
                    color: settings?.email?.mode === "smtp" ? "var(--amber)" : "var(--accent)",
                    border: settings?.email?.mode === "smtp" ? "1px solid rgba(240,168,87,0.3)" : "1px solid rgba(62,207,142,0.3)",
                  }}
                >
                  {settings?.email?.mode === "smtp" ? "LIVE (SMTP)" : "DRY RUN (SAFE)"}
                </span>
              </div>
              <div style={{ fontSize: "12px", color: "var(--muted)", lineHeight: 1.5 }}>
                Email delivery mode is controlled via <code>EMAIL_MODE</code> in <code>backend/.env</code>.
                In dry-run mode, approved emails are written as <code>.eml</code> files to <code>backend/data/outbox/</code> without sending over the network.
              </div>
            </div>

            {/* Form */}
            <form onSubmit={handleSaveSettings}>
              {/* Owner Email Field */}
              <div style={{ marginBottom: "18px" }}>
                <label className="field-label" htmlFor="owner-email">
                  Business Owner Email (Approval Recipient)
                </label>
                <input
                  id="owner-email"
                  className="field"
                  type="email"
                  value={ownerEmailInput}
                  onChange={(e) => setOwnerEmailInput(e.target.value)}
                  placeholder="e.g. owner@aaravretail.com"
                  disabled={!isOwner || savingSettings}
                  style={{ margin: 0 }}
                />
                {!isOwner && (
                  <div style={{ fontSize: "11.5px", color: "var(--faint)", marginTop: "4px" }}>
                    Read-only. Only the business owner can modify recipient settings.
                  </div>
                )}
              </div>

              {/* Reminder Toggle & Hours */}
              <div
                style={{
                  padding: "16px",
                  background: "var(--panel-2)",
                  border: "1px solid var(--border)",
                  borderRadius: "8px",
                  marginBottom: "20px",
                }}
              >
                <div style={{ display: "flex", alignItems: "center", gap: "10px", marginBottom: "8px" }}>
                  <input
                    id="reminder-toggle"
                    type="checkbox"
                    checked={reminderEnabled}
                    onChange={(e) => setReminderEnabled(e.target.checked)}
                    disabled={!isOwner || savingSettings}
                    style={{ width: "16px", height: "16px", cursor: isOwner ? "pointer" : "default" }}
                  />
                  <label htmlFor="reminder-toggle" style={{ fontSize: "13.5px", fontWeight: 600, color: "var(--text)", cursor: isOwner ? "pointer" : "default" }}>
                    Enable Overdue Action Reminder Emails (Default: Off)
                  </label>
                </div>
                <div style={{ fontSize: "12px", color: "var(--amber)", marginBottom: "12px" }}>
                  Reminder emails are sent without an approval click.
                </div>

                <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                  <span style={{ fontSize: "12.5px", color: "var(--muted)" }}>Send reminder after:</span>
                  <input
                    type="number"
                    min="1"
                    max="72"
                    value={reminderHours}
                    onChange={(e) => setReminderHours(e.target.value)}
                    disabled={!isOwner || !reminderEnabled || savingSettings}
                    className="field"
                    style={{ width: "80px", margin: 0, padding: "6px 10px" }}
                  />
                  <span style={{ fontSize: "12.5px", color: "var(--muted)" }}>hours pending approval</span>
                </div>
              </div>

              {/* Messages */}
              {settingsSavedMsg && (
                <div style={{ fontSize: "12.5px", color: "var(--accent)", marginBottom: "14px", display: "flex", alignItems: "center", gap: "6px" }}>
                  <IconCheck size={16} /> {settingsSavedMsg}
                </div>
              )}
              {settingsErrorMsg && (
                <div style={{ fontSize: "12.5px", color: "var(--red)", marginBottom: "14px" }}>
                  {settingsErrorMsg}
                </div>
              )}

              {/* Save & Test Email Buttons */}
              <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: "10px" }}>
                <div>
                  {isOwner && (
                    <button
                      type="submit"
                      className="btn primary"
                      disabled={savingSettings}
                      style={{ width: "auto", minWidth: "130px" }}
                    >
                      {savingSettings ? "Saving..." : "Save Settings"}
                    </button>
                  )}
                </div>

                {isOwner && (
                  <button
                    type="button"
                    className="btn"
                    onClick={handleSendTestEmail}
                    disabled={sendingTest || !ownerEmailInput.trim()}
                    style={{ fontSize: "12.5px", padding: "8px 16px" }}
                  >
                    {sendingTest ? "Sending test..." : "Send Test Email"}
                  </button>
                )}
              </div>
            </form>

            {/* Test Email Result */}
            {testResult && (
              <div
                style={{
                  marginTop: "16px",
                  padding: "10px 14px",
                  borderRadius: "6px",
                  fontSize: "12px",
                  background: testResult.success ? "rgba(62,207,142,0.12)" : "rgba(229,89,95,0.12)",
                  color: testResult.success ? "var(--accent)" : "var(--red)",
                  border: testResult.success ? "1px solid rgba(62,207,142,0.3)" : "1px solid rgba(229,89,95,0.3)",
                }}
              >
                {testResult.message}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
