import React, { useState, useEffect } from "react";
import { getAgentSettings, approveAction, rejectAction, getReportById, downloadReportAsFile } from "../lib/api";
import { IconX, IconCheck, IconMail, IconDownload } from "./icons";

export default function ApprovalDialog({
  action,
  reportId,
  session,
  onClose,
  onSuccess,
  onGoToSettings,
}) {
  const [settings, setSettings] = useState(null);
  const [report, setReport] = useState(null);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [rejecting, setRejecting] = useState(false);
  const [rejectReason, setRejectReason] = useState("");
  const [showRejectInput, setShowRejectInput] = useState(false);
  const [errorMsg, setErrorMsg] = useState(null);
  const [successMsg, setSuccessMsg] = useState(null);
  const [recipientEmail, setRecipientEmail] = useState("");
  const [isEditingRecipient, setIsEditingRecipient] = useState(false);

  const effectiveReportId = reportId || action?.report_id;

  useEffect(() => {
    let mounted = true;
    let localEmail = session?.email || "";
    if (!localEmail) {
      try {
        const s = JSON.parse(localStorage.getItem("finpilot_session") || "{}");
        localEmail = s.email || "";
      } catch (e) {}
    }

    Promise.all([
      getAgentSettings().catch(() => null),
      effectiveReportId ? getReportById(effectiveReportId).catch(() => null) : Promise.resolve(null),
    ]).then(([sData, rData]) => {
      if (!mounted) return;
      if (sData) setSettings(sData);
      const defaultTo = localEmail || sData?.owner_email?.trim() || "";
      setRecipientEmail(defaultTo);
      if (rData?.report) setReport(rData.report);
      setLoading(false);
    });
    return () => {
      mounted = false;
    };
  }, [effectiveReportId, session]);

  const effectiveToEmail = recipientEmail || settings?.owner_email?.trim() || "";
  const isEmailSet = Boolean(effectiveToEmail && effectiveToEmail.includes("@"));
  const emailMode = settings?.email?.mode || "dry_run";
  const isDryRun = emailMode === "dry_run";

  async function handleApprove() {
    if (!action?.id) return;
    setSubmitting(true);
    setErrorMsg(null);
    setSuccessMsg(null);
    try {
      const res = await approveAction(action.id, effectiveToEmail);
      const msg = res.email?.message || `Report approved and dispatched to ${effectiveToEmail}.`;
      setSuccessMsg(msg);
      if (onSuccess) onSuccess();
      setTimeout(() => {
        onClose();
      }, 1600);
    } catch (err) {
      setErrorMsg(err.message || "Failed to approve and send report.");
      setSubmitting(false);
    }
  }

  async function handleReject() {
    if (!action?.id) return;
    setRejecting(true);
    setErrorMsg(null);
    try {
      await rejectAction(action.id, rejectReason.trim());
      setSuccessMsg("Action rejected.");
      if (onSuccess) onSuccess();
      setTimeout(() => {
        onClose();
      }, 1200);
    } catch (err) {
      setErrorMsg(err.message || "Failed to reject action.");
      setRejecting(false);
    }
  }

  return (
    <div className="modal-backdrop" onClick={onClose} role="dialog" aria-modal="true">
      <div
        className="approval-modal"
        onClick={(e) => e.stopPropagation()}
        style={{
          maxWidth: "880px",
          width: "92vw",
          height: "88vh",
          maxHeight: "860px",
          display: "flex",
          flexDirection: "column",
          padding: 0,
          background: "var(--panel)",
          border: "1px solid var(--border)",
          borderRadius: "14px",
          overflow: "hidden",
          boxShadow: "0 24px 60px rgba(0,0,0,0.65)",
        }}
      >
        {/* Modal Header */}
        <div
          style={{
            padding: "16px 20px",
            borderBottom: "1px solid var(--border)",
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
          }}
        >
          <div>
            <h3 style={{ margin: 0, fontSize: "16px", fontWeight: 700, color: "var(--text)" }}>
              Review &amp; Approve Dispatch
            </h3>
            <div style={{ fontSize: "12px", color: "var(--muted)", marginTop: "2px" }}>
              Action {action?.id ? `#${action.id}` : "Preview"} &middot; Stored snapshot
            </div>
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
            {report?.html && (
              <button
                type="button"
                className="btn ghost"
                onClick={() => downloadReportAsFile(`FinPilot_Report_${effectiveReportId || "snapshot"}.html`, report.html, "text/html")}
                style={{ fontSize: "12px", padding: "4px 10px", width: "auto", display: "inline-flex", alignItems: "center", gap: "5px" }}
                title="Download complete report HTML offline"
              >
                <IconDownload size={13} /> HTML
              </button>
            )}
            {report?.attachment_csv && (
              <button
                type="button"
                className="btn ghost"
                onClick={() => downloadReportAsFile(`FinPilot_Report_Data_${effectiveReportId || "snapshot"}.csv`, report.attachment_csv, "text/csv")}
                style={{ fontSize: "12px", padding: "4px 10px", width: "auto", display: "inline-flex", alignItems: "center", gap: "5px" }}
                title="Download flagged transactions CSV"
              >
                <IconDownload size={13} /> CSV
              </button>
            )}
            <button
              type="button"
              onClick={onClose}
              aria-label="Close"
              style={{
                background: "none",
                border: "none",
                color: "var(--muted)",
                cursor: "pointer",
                padding: "4px",
                display: "flex",
              }}
            >
              <IconX size={20} />
            </button>
          </div>
        </div>

        {/* Mode & Email Banner */}
        <div style={{ padding: "12px 20px", background: "var(--panel-2)", borderBottom: "1px solid var(--border)" }}>
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: "8px" }}>
            <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
              <span
                style={{
                  fontFamily: "var(--font-mono)",
                  fontSize: "11px",
                  fontWeight: 700,
                  padding: "2px 8px",
                  borderRadius: "4px",
                  background: isDryRun ? "rgba(62,207,142,0.12)" : "rgba(240,168,87,0.15)",
                  color: isDryRun ? "var(--accent)" : "var(--amber)",
                  border: isDryRun ? "1px solid rgba(62,207,142,0.3)" : "1px solid rgba(240,168,87,0.3)",
                }}
              >
                {isDryRun ? "DRY RUN MODE" : "LIVE SMTP MODE"}
              </span>
              <span style={{ fontSize: "12px", color: "var(--muted)" }}>
                {isDryRun
                  ? "The email will be saved to outbox, not sent over network."
                  : `Will be emailed to ${effectiveToEmail || "configured owner email"}.`}
              </span>
            </div>
            <div style={{ fontSize: "12px", color: "var(--faint)", display: "flex", alignItems: "center", gap: "6px" }}>
              <IconMail size={14} /> To:
              {isEditingRecipient ? (
                <span style={{ display: "inline-flex", gap: "4px", alignItems: "center" }}>
                  <input
                    className="field"
                    value={recipientEmail}
                    onChange={(e) => setRecipientEmail(e.target.value)}
                    style={{ padding: "3px 8px", fontSize: "12px", margin: 0, width: "220px", height: "26px" }}
                    placeholder="email@example.com"
                    autoFocus
                  />
                  <button
                    type="button"
                    onClick={() => setIsEditingRecipient(false)}
                    style={{ background: "none", border: "none", color: "var(--accent)", fontSize: "11px", cursor: "pointer", fontWeight: 600 }}
                  >
                    Done
                  </button>
                </span>
              ) : (
                <span style={{ display: "inline-flex", alignItems: "center", gap: "6px" }}>
                  <strong style={{ color: "var(--text)" }}>{effectiveToEmail || "Not configured"}</strong>
                  <button
                    type="button"
                    onClick={() => setIsEditingRecipient(true)}
                    style={{ background: "none", border: "none", color: "var(--accent)", fontSize: "11px", cursor: "pointer", textDecoration: "underline", padding: 0 }}
                  >
                    Change
                  </button>
                </span>
              )}
            </div>
          </div>

          {!isEmailSet && (
            <div
              style={{
                marginTop: "10px",
                padding: "8px 12px",
                borderRadius: "6px",
                background: "rgba(240,168,87,0.1)",
                border: "1px solid rgba(240,168,87,0.3)",
                fontSize: "12px",
                color: "var(--amber)",
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
              }}
            >
              <span>Set the owner's email in Settings first before approving.</span>
              {onGoToSettings && (
                <button
                  type="button"
                  onClick={() => {
                    onClose();
                    onGoToSettings();
                  }}
                  style={{
                    background: "none",
                    border: "none",
                    color: "var(--accent)",
                    fontWeight: 600,
                    textDecoration: "underline",
                    cursor: "pointer",
                    fontSize: "12px",
                  }}
                >
                  Open Settings &rarr;
                </button>
              )}
            </div>
          )}
        </div>

        {/* Email Meta bar */}
        <div style={{ padding: "10px 20px", borderBottom: "1px solid var(--border)", background: "rgba(0,0,0,0.2)" }}>
          <div style={{ fontSize: "12.5px", color: "var(--muted)" }}>
            Subject: <span style={{ color: "var(--text)", fontWeight: 600 }}>{report?.subject || action?.title || "Loading report..."}</span>
          </div>
        </div>

        {/* Sandboxed Iframe Preview */}
        <div style={{ flex: 1, minHeight: 0, height: "100%", background: "#FFFFFF", overflow: "hidden", position: "relative" }}>
          {loading ? (
            <div style={{ padding: "40px", textAlign: "center", color: "#5B6475", background: "#F3F5F8", height: "100%" }}>
              Loading report snapshot preview...
            </div>
          ) : report?.html ? (
            <iframe
              title="Report Email Preview"
              srcDoc={report.html}
              sandbox=""
              style={{
                width: "100%",
                height: "100%",
                border: "none",
                display: "block",
                background: "#F3F5F8",
              }}
            />
          ) : (
            <div style={{ padding: "40px", textAlign: "center", color: "#5B6475", background: "#F3F5F8", height: "100%" }}>
              No HTML snapshot available for this action.
            </div>
          )}
        </div>

        {/* Error / Success Feedback */}
        {errorMsg && (
          <div
            style={{
              padding: "10px 20px",
              background: "rgba(229,89,95,0.15)",
              borderTop: "1px solid rgba(229,89,95,0.3)",
              color: "var(--red)",
              fontSize: "12.5px",
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
            }}
          >
            <span>{errorMsg}</span>
            <button
              type="button"
              className="btn"
              onClick={handleApprove}
              disabled={submitting || !isEmailSet}
              style={{ padding: "4px 10px", fontSize: "11.5px", background: "var(--red)", color: "#fff", border: "none" }}
            >
              Retry
            </button>
          </div>
        )}

        {successMsg && (
          <div
            style={{
              padding: "10px 20px",
              background: "rgba(62,207,142,0.15)",
              borderTop: "1px solid rgba(62,207,142,0.3)",
              color: "var(--accent)",
              fontSize: "12.5px",
              display: "flex",
              alignItems: "center",
              gap: "8px",
            }}
          >
            <IconCheck size={16} />
            <span>{successMsg}</span>
          </div>
        )}

        {/* Rejection reason box */}
        {showRejectInput && !successMsg && (
          <div style={{ padding: "12px 20px", borderTop: "1px solid var(--border)", background: "var(--panel-2)" }}>
            <label style={{ display: "block", fontSize: "12px", color: "var(--muted)", marginBottom: "6px" }}>
              Reason for rejection (optional):
            </label>
            <div style={{ display: "flex", gap: "8px" }}>
              <input
                className="field"
                value={rejectReason}
                onChange={(e) => setRejectReason(e.target.value)}
                placeholder="e.g. Expected seasonal spike or already reviewed"
                style={{ margin: 0 }}
                autoFocus
              />
              <button
                type="button"
                className="btn danger-btn"
                onClick={handleReject}
                disabled={rejecting}
                style={{ padding: "0 16px", whiteSpace: "nowrap" }}
              >
                {rejecting ? "Rejecting..." : "Confirm Reject"}
              </button>
              <button
                type="button"
                className="btn"
                onClick={() => setShowRejectInput(false)}
                disabled={rejecting}
              >
                Cancel
              </button>
            </div>
          </div>
        )}

        {/* Modal Actions Footer */}
        {!showRejectInput && (
          <div
            style={{
              padding: "14px 20px",
              borderTop: "1px solid var(--border)",
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              background: "var(--panel)",
            }}
          >
            <div>
              {action?.status !== "executed" && action?.status !== "rejected" && (
                <button
                  type="button"
                  className="btn"
                  onClick={() => setShowRejectInput(true)}
                  disabled={submitting || successMsg}
                  style={{ color: "var(--red)", borderColor: "rgba(229,89,95,0.3)" }}
                >
                  Reject action
                </button>
              )}
            </div>

            <div style={{ display: "flex", gap: "10px" }}>
              <button type="button" className="btn" onClick={onClose} disabled={submitting}>
                Cancel
              </button>
              {action?.status !== "executed" && action?.status !== "rejected" && (
                <button
                  type="button"
                  className="btn primary"
                  onClick={handleApprove}
                  disabled={submitting || !isEmailSet || Boolean(successMsg)}
                  style={{ width: "auto", minWidth: "150px" }}
                >
                  {submitting ? "Sending..." : "Approve & send"}
                </button>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
