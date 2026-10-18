import React, { useState, useEffect, useRef, useMemo } from "react";
import {
  uploadFraudCsv,
  getFraudHistory,
  clearFraudHistory,
} from "../lib/api";
import {
  IconFraud,
  IconUpload,
  IconTrash,
  IconCalendar,
  IconDownload,
  IconChevronDown,
  IconChevronUp,
} from "./icons";

function getOrdinalSuffix(day) {
  if (day > 3 && day < 21) return "th";
  switch (day % 10) {
    case 1:
      return "st";
    case 2:
      return "nd";
    case 3:
      return "rd";
    default:
      return "th";
  }
}

export function formatBatchDate(isoString) {
  if (!isoString) return "";
  const d = new Date(isoString);
  const day = d.getDate();
  const suffix = getOrdinalSuffix(day);
  const month = d.toLocaleString("en-US", { month: "short" });
  const year = d.getFullYear();
  const hours24 = d.getHours();
  const period = hours24 >= 12 ? "PM" : "AM";
  const hours12 = hours24 % 12 || 12;
  return `${day}${suffix} ${month} ${year}, ${hours12}:00 ${period}`;
}

export function formatDateOnly(isoString) {
  if (!isoString) return "";
  const d = new Date(isoString);
  const day = d.getDate();
  const suffix = getOrdinalSuffix(day);
  const month = d.toLocaleString("en-US", { month: "short" });
  const year = d.getFullYear();
  return `${day}${suffix} ${month} ${year}`;
}

export function getDateKey(isoString) {
  if (!isoString) return "";
  const d = new Date(isoString);
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}

const currencyFormatter = new Intl.NumberFormat("en-IN", {
  style: "currency",
  currency: "INR",
});

function downloadTemplate() {
  const csvContent =
    "transaction_id,customer_id,amount,transaction_frequency,average_amount,time_interval_minutes,location_change,device_change,transaction_datetime,location,device,payment_method\n" +
    "TX1001,C101,450.00,2,420.00,120,false,false,2026-10-18 10:30:00,Mumbai,Mobile_App,UPI\n" +
    "TX1002,C102,12500.00,8,650.00,5,true,true,2026-10-18 11:15:00,Delhi,Web_Browser,Credit_Card\n" +
    "TX1003,C103,1200.00,1,1100.00,720,false,false,2026-10-18 14:00:00,Bengaluru,POS_Terminal,Debit_Card\n";
  const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = "finpilot_fraud_template.csv";
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

export default function FraudTab({ session, onHistoryChange }) {
  const [historyData, setHistoryData] = useState(null);
  const [loadingHistory, setLoadingHistory] = useState(true);
  const [historyError, setHistoryError] = useState(null);

  // Upload state
  const [uploading, setUploading] = useState(false);
  const [uploadStatus, setUploadStatus] = useState(null); // { type: 'success'|'error', message }
  const [isDragging, setIsDragging] = useState(false);
  const [showColumnsHint, setShowColumnsHint] = useState(false);
  const fileInputRef = useRef(null);

  // Expanded cards state
  const [expandedBatches, setExpandedBatches] = useState({});
  const [expandedRows, setExpandedRows] = useState({});
  const [showAllRowsBatches, setShowAllRowsBatches] = useState({});
  const [highlightedBatchId, setHighlightedBatchId] = useState(null);

  // Clear modal state
  const [showClearModal, setShowClearModal] = useState(false);
  const [clearing, setClearing] = useState(false);

  // Date jump selection
  const [selectedDateKey, setSelectedDateKey] = useState("");

  const isOwner = session?.role === "owner";

  async function loadHistory(targetBatchIdToExpand = null) {
    setLoadingHistory(true);
    setHistoryError(null);
    try {
      const data = await getFraudHistory();
      setHistoryData(data);
      if (onHistoryChange) {
        onHistoryChange(data);
      }
      // Expand newest batch by default, or specific batch
      if (data?.batches?.length > 0) {
        setExpandedBatches((prev) => {
          const next = { ...prev };
          if (targetBatchIdToExpand) {
            next[targetBatchIdToExpand] = true;
          } else {
            // Newest batch is index 0
            next[data.batches[0].id] = true;
          }
          return next;
        });
      }
    } catch (err) {
      setHistoryError(err.message || "Couldn't load history");
    } finally {
      setLoadingHistory(false);
    }
  }

  useEffect(() => {
    loadHistory();
  }, []);

  const batches = historyData?.batches || [];
  const totals = historyData?.totals || { batches: 0, transactions: 0, suspicious: 0 };

  // Distinct dates for "Jump to date" dropdown
  const distinctDates = useMemo(() => {
    const list = [];
    const seen = new Set();
    const countMap = {};

    batches.forEach((b) => {
      const key = getDateKey(b.uploaded_at);
      countMap[key] = (countMap[key] || 0) + 1;
      if (!seen.has(key)) {
        seen.add(key);
        list.push({
          key,
          dateLabel: formatDateOnly(b.uploaded_at),
          newestBatchId: b.id,
        });
      }
    });

    return list.map((item) => {
      const cnt = countMap[item.key];
      return {
        ...item,
        displayLabel: cnt > 1 ? `${item.dateLabel} (${cnt} uploads)` : item.dateLabel,
      };
    });
  }, [batches]);

  async function handleFile(file) {
    if (!file) return;

    if (!file.name.toLowerCase().endsWith(".csv")) {
      setUploadStatus({
        type: "error",
        message: "Please upload a valid CSV file (.csv).",
      });
      return;
    }

    setUploading(true);
    setUploadStatus(null);

    try {
      const res = await uploadFraudCsv(file);
      const newBatch = res.batch;
      setUploadStatus({
        type: "success",
        message: `${newBatch.total} transactions scored, ${newBatch.suspicious} suspicious`,
      });

      // Reload history and highlight/scroll to new batch
      await loadHistory(newBatch.id);

      setTimeout(() => {
        scrollToBatch(newBatch.id);
      }, 100);
    } catch (err) {
      setUploadStatus({
        type: "error",
        message: err.message || "Failed to score transactions.",
      });
    } finally {
      setUploading(false);
    }
  }

  function scrollToBatch(batchId) {
    setExpandedBatches((prev) => ({ ...prev, [batchId]: true }));
    setHighlightedBatchId(batchId);
    const el = document.getElementById(`batch-card-${batchId}`);
    if (el) {
      const prefersReducedMotion =
        typeof window !== "undefined" &&
        window.matchMedia("(prefers-reduced-motion: reduce)").matches;
      el.scrollIntoView({
        behavior: prefersReducedMotion ? "auto" : "smooth",
        block: "start",
      });
    }
    setTimeout(() => {
      setHighlightedBatchId((prev) => (prev === batchId ? null : prev));
    }, 2200);
  }

  function handleDateJump(dateKey) {
    setSelectedDateKey(dateKey);
    if (!dateKey) return;
    const target = distinctDates.find((d) => d.key === dateKey);
    if (target) {
      scrollToBatch(target.newestBatchId);
    }
  }

  async function handleConfirmClear() {
    setClearing(true);
    try {
      await clearFraudHistory();
      setShowClearModal(false);
      setSelectedDateKey("");
      setUploadStatus(null);
      await loadHistory();
    } catch (err) {
      alert(err.message || "Failed to clear history");
    } finally {
      setClearing(false);
    }
  }

  function toggleBatch(batchId) {
    setExpandedBatches((prev) => ({
      ...prev,
      [batchId]: !prev[batchId],
    }));
  }

  function toggleRow(key) {
    setExpandedRows((prev) => ({
      ...prev,
      [key]: !prev[key],
    }));
  }

  function toggleShowAllRows(batchId) {
    setShowAllRowsBatches((prev) => ({
      ...prev,
      [batchId]: !prev[batchId],
    }));
  }

  return (
    <div className="fraud-tab-root">
      {/* 1. Header */}
      <div className="topbar">
        <div>
          <h2>Fraud alerts</h2>
          <div className="sub">
            Rule-based risk scoring + Isolation Forest anomaly detection · served from /api/v1/fraud
          </div>
        </div>
        <span className="pill">
          {totals.suspicious} suspicious / {totals.transactions} scored · {totals.batches}{" "}
          {totals.batches === 1 ? "upload" : "uploads"}
        </span>
      </div>

      {/* 2. Upload Card */}
      <div className="card fraud-upload-card" style={{ marginBottom: 20 }}>
        <div
          className={`fraud-upload-zone ${isDragging ? "dragging" : ""} ${uploading ? "uploading" : ""}`}
          onDragOver={(e) => {
            e.preventDefault();
            if (!uploading) setIsDragging(true);
          }}
          onDragLeave={() => setIsDragging(false)}
          onDrop={(e) => {
            e.preventDefault();
            setIsDragging(false);
            if (uploading) return;
            const file = e.dataTransfer.files?.[0];
            if (file) handleFile(file);
          }}
        >
          <input
            ref={fileInputRef}
            type="file"
            accept=".csv,text/csv"
            style={{ display: "none" }}
            onChange={(e) => {
              const f = e.target.files?.[0];
              if (f) handleFile(f);
              e.target.value = "";
            }}
          />

          <div className="upload-icon-wrap">
            <IconUpload size={32} />
          </div>

          <p className="upload-main-text">
            Upload a CSV of transactions. The model scores every row and adds the results below.
          </p>

          <div style={{ display: "flex", gap: 12, alignItems: "center", justifyContent: "center", flexWrap: "wrap" }}>
            <button
              type="button"
              className="btn primary"
              style={{ width: "auto", minWidth: 140 }}
              disabled={uploading}
              onClick={() => fileInputRef.current?.click()}
            >
              {uploading ? "Scoring transactions…" : "Browse CSV file"}
            </button>

            <button
              type="button"
              className="btn ghost"
              style={{ width: "auto", display: "inline-flex", alignItems: "center", gap: 6, fontSize: 12.5 }}
              onClick={downloadTemplate}
              title="Download a CSV template with sample rows"
            >
              <IconDownload size={15} />
              <span>Download template</span>
            </button>
          </div>

          {/* Required columns collapsible hint */}
          <div style={{ marginTop: 14 }}>
            <button
              type="button"
              className="hint-toggle-btn"
              onClick={() => setShowColumnsHint((prev) => !prev)}
              aria-expanded={showColumnsHint}
            >
              <span>{showColumnsHint ? "Hide required columns" : "View required columns"}</span>
              {showColumnsHint ? <IconChevronUp size={14} /> : <IconChevronDown size={14} />}
            </button>

            {showColumnsHint && (
              <div className="columns-hint-box">
                <div style={{ marginBottom: 6 }}>
                  <strong style={{ color: "var(--text)" }}>Required columns (6):</strong>{" "}
                  <code>amount</code>, <code>transaction_frequency</code>, <code>average_amount</code>,{" "}
                  <code>time_interval_minutes</code>, <code>location_change</code>, <code>device_change</code>{" "}
                  <span style={{ color: "var(--faint)" }}>(last two accept true/false, 1/0, yes/no)</span>
                </div>
                <div>
                  <strong style={{ color: "var(--text)" }}>Optional columns:</strong>{" "}
                  <code>transaction_id</code>, <code>customer_id</code>, <code>transaction_datetime</code>,{" "}
                  <code>location</code>, <code>device</code>, <code>payment_method</code>
                </div>
              </div>
            )}
          </div>
        </div>

        {uploadStatus && (
          <div className={`upload-status-banner ${uploadStatus.type}`} style={{ marginTop: 14 }}>
            {uploadStatus.message}
          </div>
        )}
      </div>

      {/* 3. Sticky Toolbar Row */}
      <div className="fraud-sticky-toolbar">
        <div className="toolbar-left">
          <div className="date-select-wrap">
            <span className="date-select-icon">
              <IconCalendar size={16} />
            </span>
            <select
              className="date-select"
              value={selectedDateKey}
              onChange={(e) => handleDateJump(e.target.value)}
              disabled={distinctDates.length === 0}
            >
              <option value="">Jump to date...</option>
              {distinctDates.map((d) => (
                <option key={d.key} value={d.key}>
                  {d.displayLabel}
                </option>
              ))}
            </select>
          </div>
        </div>

        <div className="toolbar-right">
          <button
            type="button"
            className="btn clear-history-btn"
            disabled={!isOwner || totals.batches === 0}
            title={!isOwner ? "Only the Owner can clear history" : "Clear all fraud uploads"}
            onClick={() => setShowClearModal(true)}
          >
            <IconTrash size={16} />
            <span>Clear history</span>
          </button>
        </div>
      </div>

      {/* 4. Timeline / Cards */}
      {loadingHistory && !historyData ? (
        <div className="loading" style={{ padding: "30px 0", textAlign: "center" }}>
          Loading fraud history…
        </div>
      ) : historyError ? (
        <div className="card" style={{ textAlign: "center", padding: "30px 20px" }}>
          <div style={{ color: "var(--red)", marginBottom: 10 }}>{historyError}</div>
          <button type="button" className="btn ghost" onClick={() => loadHistory()}>
            Retry
          </button>
        </div>
      ) : batches.length === 0 ? (
        /* 5. Empty State */
        <div className="card fraud-empty-card">
          <div className="empty-icon-box">
            <IconFraud size={40} />
          </div>
          <h3>No transactions yet</h3>
          <p className="empty-subtext">
            Upload a CSV to see risk scores here. The model flags anomalies and high-risk transactions.
          </p>
          <button
            type="button"
            className="btn ghost"
            style={{ display: "inline-flex", alignItems: "center", gap: 6, fontSize: 13, marginTop: 10 }}
            onClick={downloadTemplate}
          >
            <IconDownload size={16} />
            <span>Download template CSV</span>
          </button>
        </div>
      ) : (
        <div className="fraud-timeline">
          {batches.map((batch) => {
            const isExpanded = !!expandedBatches[batch.id];
            const isHighlighted = highlightedBatchId === batch.id;
            const formattedHeaderDate = formatBatchDate(batch.uploaded_at);
            const showAll = !!showAllRowsBatches[batch.id];
            const transactions = batch.transactions || [];
            const displayRows = showAll ? transactions : transactions.slice(0, 200);

            // Find divider position between suspicious and normal
            let firstNormalIndex = -1;
            for (let i = 0; i < displayRows.length; i++) {
              if (displayRows[i].status !== "SUSPICIOUS") {
                firstNormalIndex = i;
                break;
              }
            }

            return (
              <div
                key={`batch-card-${batch.id}`}
                id={`batch-card-${batch.id}`}
                className={`card fraud-batch-card ${isHighlighted ? "highlighted" : ""}`}
              >
                {/* Batch Card Header */}
                <div
                  className="batch-header"
                  onClick={() => toggleBatch(batch.id)}
                  role="button"
                  tabIndex={0}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" || e.key === " ") {
                      e.preventDefault();
                      toggleBatch(batch.id);
                    }
                  }}
                  aria-expanded={isExpanded}
                >
                  <div className="batch-header-info">
                    <div className="batch-date-title">{formattedHeaderDate}</div>
                    <div className="batch-meta-row">
                      <span className="batch-filename">{batch.filename}</span>
                      <span className="meta-chip total">{batch.total} scored</span>
                      <span className="meta-chip susp">{batch.suspicious} suspicious</span>
                      <span className="meta-chip norm">{batch.normal} normal</span>
                    </div>
                  </div>

                  <div className="batch-toggle-icon">
                    {isExpanded ? <IconChevronUp size={20} /> : <IconChevronDown size={20} />}
                  </div>
                </div>

                {/* Batch Table Content */}
                {isExpanded && (
                  <div className="batch-content">
                    <div className="table-responsive">
                      <table>
                        <thead>
                          <tr>
                            <th>Transaction</th>
                            <th>Customer</th>
                            <th>Amount</th>
                            <th style={{ minWidth: 140 }}>Risk score</th>
                            <th>Status</th>
                            <th style={{ width: 40 }}></th>
                          </tr>
                        </thead>
                        <tbody>
                          {displayRows.map((tx, idx) => {
                            const isSuspicious = tx.status === "SUSPICIOUS";
                            const rowKey = `batch-${batch.id}-tx-${tx.rank}`;
                            const isRowExpanded = !!expandedRows[rowKey];

                            // Risk bar color: red at >= 50, amber 25-49, green < 25
                            const score = Number(tx.risk_score || 0);
                            const riskLevel = score >= 50 ? "high" : score >= 25 ? "med" : "low";

                            // Check if this row is the start of normal rows (after suspicious)
                            const showDivider = idx === firstNormalIndex && firstNormalIndex > 0;

                            return (
                              <React.Fragment key={rowKey}>
                                {showDivider && (
                                  <tr className="table-divider-row">
                                    <td colSpan={6}>
                                      <div className="divider-label">
                                        <span>Normal transactions</span>
                                      </div>
                                    </td>
                                  </tr>
                                )}

                                <tr
                                  className={`tx-row ${isSuspicious ? "suspicious-row" : "normal-row"} ${
                                    isRowExpanded ? "row-expanded" : ""
                                  }`}
                                  onClick={() => toggleRow(rowKey)}
                                  style={{ cursor: "pointer" }}
                                >
                                  <td className="amt">{tx.transaction_id || "—"}</td>
                                  <td>{tx.customer_id || "—"}</td>
                                  <td className="amt">{currencyFormatter.format(tx.amount || 0)}</td>
                                  <td>
                                    <div className="risk-cell">
                                      <span className={`risk ${riskLevel}`}>{score.toFixed(1)}</span>
                                      <div className="risk-bar-track">
                                        <div
                                          className={`risk-bar-fill ${riskLevel}`}
                                          style={{ width: `${Math.min(100, Math.max(4, score))}%` }}
                                        />
                                      </div>
                                    </div>
                                  </td>
                                  <td>
                                    <span className={`status-pill ${isSuspicious ? "pill-susp" : "pill-norm"}`}>
                                      {tx.status}
                                    </span>
                                  </td>
                                  <td style={{ textAlign: "right" }}>
                                    <button
                                      type="button"
                                      className="row-expand-btn"
                                      aria-label={isRowExpanded ? "Collapse details" : "Expand details"}
                                      onClick={(e) => {
                                        e.stopPropagation();
                                        toggleRow(rowKey);
                                      }}
                                    >
                                      {isRowExpanded ? <IconChevronUp size={16} /> : <IconChevronDown size={16} />}
                                    </button>
                                  </td>
                                </tr>

                                {isRowExpanded && (
                                  <tr className="tx-details-row">
                                    <td colSpan={6}>
                                      <div className="tx-details-panel">
                                        <div className="detail-section">
                                          <div className="detail-heading">Model assessment:</div>
                                          <div className="reasons-chips">
                                            {tx.reasons && tx.reasons.length > 0 ? (
                                              tx.reasons.map((r, rIdx) => (
                                                <span key={rIdx} className="reason-chip">
                                                  {String(r)}
                                                </span>
                                              ))
                                            ) : (
                                              <span className="reason-chip faint">No specific rules triggered</span>
                                            )}
                                          </div>
                                        </div>

                                        <div className="detail-meta-grid">
                                          <div className="detail-item">
                                            <span className="d-label">AI Anomaly score:</span>
                                            <span className="d-val amt">
                                              {tx.ai_anomaly_score !== null && tx.ai_anomaly_score !== undefined
                                                ? Number(tx.ai_anomaly_score).toFixed(4)
                                                : "—"}
                                            </span>
                                          </div>
                                          <div className="detail-item">
                                            <span className="d-label">Isolation Forest:</span>
                                            <span className="d-val">
                                              {tx.ai_flagged ? "Flagged as anomaly" : "Normal"}
                                            </span>
                                          </div>

                                          {tx.details?.location && (
                                            <div className="detail-item">
                                              <span className="d-label">Location:</span>
                                              <span className="d-val">{String(tx.details.location)}</span>
                                            </div>
                                          )}

                                          {tx.details?.device && (
                                            <div className="detail-item">
                                              <span className="d-label">Device:</span>
                                              <span className="d-val">{String(tx.details.device)}</span>
                                            </div>
                                          )}

                                          {tx.details?.payment_method && (
                                            <div className="detail-item">
                                              <span className="d-label">Payment method:</span>
                                              <span className="d-val">{String(tx.details.payment_method)}</span>
                                            </div>
                                          )}

                                          {tx.details?.transaction_datetime && (
                                            <div className="detail-item">
                                              <span className="d-label">Date & Time:</span>
                                              <span className="d-val">{String(tx.details.transaction_datetime)}</span>
                                            </div>
                                          )}
                                        </div>
                                      </div>
                                    </td>
                                  </tr>
                                )}
                              </React.Fragment>
                            );
                          })}
                        </tbody>
                      </table>
                    </div>

                    {/* Pagination / Show all button */}
                    {transactions.length > 200 && (
                      <div className="show-more-wrap">
                        <button
                          type="button"
                          className="btn ghost"
                          onClick={() => toggleShowAllRows(batch.id)}
                        >
                          {showAll
                            ? "Show first 200 rows"
                            : `Show all ${transactions.length} rows (${transactions.length - 200} more)`}
                        </button>
                      </div>
                    )}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}

      {/* Confirmation Modal */}
      {showClearModal && (
        <div className="modal-backdrop">
          <div className="confirm-modal card" role="dialog" aria-modal="true" aria-labelledby="clear-modal-title">
            <h3 id="clear-modal-title" style={{ margin: "0 0 10px", fontSize: 16 }}>
              Clear fraud history
            </h3>
            <p style={{ color: "var(--muted)", fontSize: 13.5, lineHeight: 1.5, margin: "0 0 20px" }}>
              Clear all {totals.batches} {totals.batches === 1 ? "upload" : "uploads"} and {totals.transactions}{" "}
              {totals.transactions === 1 ? "transaction" : "transactions"}? This cannot be undone.
            </p>

            <div style={{ display: "flex", gap: 10, justifyContent: "flex-end" }}>
              <button
                type="button"
                className="btn ghost"
                style={{ width: "auto" }}
                disabled={clearing}
                onClick={() => setShowClearModal(false)}
              >
                Cancel
              </button>
              <button
                type="button"
                className="btn danger-btn"
                style={{ width: "auto" }}
                disabled={clearing}
                onClick={handleConfirmClear}
              >
                {clearing ? "Clearing…" : "Clear history"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
