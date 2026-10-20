import { useEffect, useState, useRef } from "react";
import { useRouter } from "next/router";
import ProductForecastTab from "../components/ProductForecastTab";
import Sidebar from "../components/Sidebar";
import FraudTab from "../components/FraudTab";
import NotificationsTab from "../components/NotificationsTab";
import ReportsTab from "../components/ReportsTab";
import AgentActivityTab from "../components/AgentActivityTab";
import ApprovalDialog from "../components/ApprovalDialog";
import { IconBell } from "../components/icons";
import {
  getSession,
  logout,
  getForecastSummary,
  getForecastNextWeek,
  getFlaggedTransactions,
  reviewTransaction,
  askDocuments,
  uploadDocument,
  listDocuments,
  deleteDocument,
  getDocumentEvalSummary,
  getAgentActions,
  approveAction,
  getUnreadNotificationCount,
} from "../lib/api";

export default function Dashboard() {
  const router = useRouter();
  const [session, setSession] = useState(null);
  const [tab, setTab] = useState("overview");
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);

  const [summary, setSummary] = useState(null);
  const [nextWeekItems, setNextWeekItems] = useState([]);
  const [fraud, setFraud] = useState(null);
  const [actions, setActions] = useState(null);
  const [unreadCount, setUnreadCount] = useState(0);
  const [activeApprovalAction, setActiveApprovalAction] = useState(null);

  const [documents, setDocuments] = useState([]);
  const [evalSummary, setEvalSummary] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [deletingFile, setDeletingFile] = useState(null);
  const [uploadSuccess, setUploadSuccess] = useState(null);
  const [uploadError, setUploadError] = useState(null);
  const [isDragging, setIsDragging] = useState(false);
  const fileInputRef = useRef(null);

  const [chatLog, setChatLog] = useState([
    { role: "bot", text: "Hi, I'm the FinPilot document assistant. Ask about your invoices and statements — I'll cite the source." },
  ]);
  const [chatInput, setChatInput] = useState("");
  const [typing, setTyping] = useState(false);

  function loadDocuments() {
    listDocuments()
      .then((res) => setDocuments(res.documents || []))
      .catch(() => setDocuments([]));
  }

  function refreshUnread() {
    getUnreadNotificationCount()
      .then((res) => setUnreadCount(res.count || 0))
      .catch(() => {});
  }

  useEffect(() => {
    const s = getSession();
    if (!s) {
      router.push("/");
      return;
    }
    setSession(s);
    try {
      const saved = localStorage.getItem("finpilot.sidebar");
      if (saved !== null) {
        setSidebarCollapsed(saved === "true");
      } else if (window.innerWidth < 820) {
        setSidebarCollapsed(true);
      }
    } catch (e) {}

    getForecastSummary().then(setSummary).catch(() => {});
    getForecastNextWeek().then((res) => setNextWeekItems(res.items || [])).catch(() => {});
    getFlaggedTransactions().then(setFraud).catch(() => {});
    getAgentActions().then(setActions).catch(() => {});
    getDocumentEvalSummary().then(setEvalSummary).catch(() => setEvalSummary(null));
    loadDocuments();
    refreshUnread();

    const interval = setInterval(() => {
      refreshUnread();
    }, 30000);

    function onVisibilityChange() {
      if (!document.hidden) {
        refreshUnread();
      }
    }
    document.addEventListener("visibilitychange", onVisibilityChange);

    return () => {
      clearInterval(interval);
      document.removeEventListener("visibilitychange", onVisibilityChange);
    };
  }, []);

  useEffect(() => {
    if (tab === "chat") {
      loadDocuments();
    } else if (tab === "agent") {
      getAgentActions().then(setActions).catch(() => {});
    }
  }, [tab]);

  function handleLogout() {
    logout();
    router.push("/");
  }

  async function handleReview(id, decision) {
    await reviewTransaction(id, decision);
    getFlaggedTransactions().then(setFraud);
  }

  async function handleFileUpload(file) {
    if (!file) return;
    setUploading(true);
    setUploadError(null);
    setUploadSuccess(null);
    try {
      const res = await uploadDocument(file);
      const chunkText = `${res.chunks} chunk${res.chunks === 1 ? "" : "s"}`;
      setUploadSuccess(`${res.filename} indexed (${chunkText})`);
      loadDocuments();
    } catch (err) {
      setUploadError(err.message || "Upload failed");
    } finally {
      setUploading(false);
    }
  }

  async function handleDeleteDocument(filename) {
    if (deletingFile) return;
    setDeletingFile(filename);
    setUploadError(null);
    setUploadSuccess(null);
    try {
      await deleteDocument(filename);
      loadDocuments();
    } catch (err) {
      setUploadError(err.message || "Failed to delete document");
    } finally {
      setDeletingFile(null);
    }
  }

  function sendChat(text) {
    const q = (text ?? chatInput).trim();
    if (!q || typing) return;
    setChatLog((log) => [...log, { role: "user", text: q }]);
    setChatInput("");
    setTyping(true);

    askDocuments(q)
      .then((res) => {
        setTyping(false);
        setChatLog((log) => [...log, { role: "bot", text: res.answer, sources: res.sources }]);
      })
      .catch((err) => {
        setTyping(false);
        setChatLog((log) => [...log, { role: "bot", text: err.message || "Couldn't reach the document service." }]);
      });
  }

  if (!session) return null;

  const flagged = fraud?.transactions ?? [];
  const pendingCount = flagged.filter((t) => t.status === "pending").length;
  const pendingActions = (actions?.actions ?? []).filter((a) => a.status === "pending_approval" || a.status === "failed").length;

  const top8Items = [...nextWeekItems]
    .sort((a, b) => b.predicted_sales - a.predicted_sales)
    .slice(0, 8);
  const maxTop8 = top8Items.length > 0 ? top8Items[0].predicted_sales : 1;
  const hasSampleInvoices = documents.some(
    (d) => d.filename === "sample_invoice.pdf" || d.filename === "sample_invoice_2.pdf"
  );

  return (
    <div className={`shell ${sidebarCollapsed ? "sidebar-collapsed" : "sidebar-expanded"}`}>
      <Sidebar
        tab={tab}
        setTab={setTab}
        session={session}
        onLogout={handleLogout}
        collapsed={sidebarCollapsed}
        setCollapsed={setSidebarCollapsed}
        unreadCount={unreadCount}
      />

      <main>
        {/* Global slim topbar with notification bell on every page */}
        <div
          className="global-topbar"
          style={{
            display: "flex",
            justifyContent: "flex-end",
            alignItems: "center",
            padding: "0 0 16px 0",
            marginBottom: "6px",
          }}
        >
          <button
            type="button"
            className="global-bell-btn"
            onClick={() => setTab("notifications")}
            aria-label={`Notifications, ${unreadCount} unread`}
            title={unreadCount > 0 ? `${unreadCount} unread notifications` : "Notifications"}
            style={{
              background: tab === "notifications" ? "rgba(62,207,142,0.12)" : "var(--panel)",
              border: `1px solid ${tab === "notifications" ? "var(--accent)" : "var(--border)"}`,
              borderRadius: "8px",
              padding: "7px 11px",
              color: tab === "notifications" ? "var(--accent)" : "var(--text)",
              cursor: "pointer",
              display: "flex",
              alignItems: "center",
              gap: "7px",
              position: "relative",
              transition: "background 0.15s, border-color 0.15s, color 0.15s",
            }}
          >
            <IconBell size={18} />
            {unreadCount > 0 && (
              <span
                style={{
                  background: "var(--accent)",
                  color: "#08120D",
                  fontSize: "11px",
                  fontWeight: 800,
                  padding: "1px 6px",
                  borderRadius: "10px",
                  lineHeight: 1.3,
                }}
              >
                {unreadCount > 9 ? "9+" : unreadCount}
              </span>
            )}
          </button>
        </div>

        {tab === "overview" && (
          <div>
            <div className="topbar">
              <div>
                <h2>Overview</h2>
                <div className="sub">Autonomous Financial Analyst · live from FastAPI</div>
              </div>
              <span className="pill">
                <span className="dot pulse"></span>FastAPI live · /api/v1
              </span>
            </div>

            <div className="kpirow">
              <div className="kpi">
                <div className="klabel">Next 4 weeks forecast</div>
                <div className="kval up">
                  {summary ? `$${(summary.next_4_weeks_total / 1000).toFixed(1)}K` : "…"}
                </div>
                <div className="kdelta">
                  {summary?.metrics
                    ? `WAPE ${Math.round(summary.metrics.wape_pct)}% · RMSE ${Math.round(summary.metrics.rmse).toLocaleString("en-US")}`
                    : "loading"}
                </div>
              </div>
              <div className="kpi">
                <div className="klabel">Next week total</div>
                <div className="kval">
                  {summary ? `$${(summary.next_week_total / 1000).toFixed(1)}K` : "…"}
                </div>
                <div className="kdelta">across 17 sub-categories</div>
              </div>
              <div className="kpi">
                <div className="klabel">Flagged transactions</div>
                <div className="kval warn">{pendingCount}</div>
                <div className="kdelta">awaiting review</div>
              </div>
              <div className="kpi">
                <div className="klabel">Agent actions pending</div>
                <div className="kval">{pendingActions}</div>
                <div className="kdelta">requires human approval</div>
              </div>
            </div>

            <div className="grid">
              <div className="card">
                <h3>Top sub-categories next week</h3>
                <div className="sub">Ranked by projected demand</div>
                {top8Items.length === 0 ? (
                  <div className="loading">Loading forecast data…</div>
                ) : (
                  <div className="bars">
                    {top8Items.map((item) => {
                      const pct = Math.max(4, Math.round((item.predicted_sales / maxTop8) * 100));
                      return (
                        <div key={item.sub_category} className="bar-row">
                          <span className="bar-label">{item.sub_category}</span>
                          <div className="bar-track">
                            <div className="bar-fill" style={{ width: `${pct}%` }}></div>
                          </div>
                          <span className="bar-val">
                            ${Math.round(item.predicted_sales).toLocaleString("en-US")}
                          </span>
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>

              <div className="card">
                <h3>Live summary</h3>
                <div className="sub">Current system state across all modules</div>
                <ul className="agent-highlights">
                  <li>
                    <strong>Forecasting:</strong> Ridge regression trained on 4 years of weekly sales.
                  </li>
                  <li>
                    <strong>Fraud detector:</strong> Isolation Forest + rule heuristics; pending reviews require analyst or owner approval.
                  </li>
                  <li>
                    <strong>Document store:</strong> {documents.length} document{documents.length === 1 ? "" : "s"} indexed in SQLite.
                  </li>
                  <li>
                    <strong>Approval gate:</strong> Notifications and actions queued; nothing sent without human click.
                  </li>
                </ul>
              </div>
            </div>
          </div>
        )}

        {tab === "forecast" && <ProductForecastTab />}

        {tab === "fraud" && (
          <FraudTab
            session={session}
            onHistoryChange={() => {}}
            onBatchUploaded={refreshUnread}
            onNavigateTab={setTab}
          />
        )}

        {tab === "chat" && (
          <div>
            <div className="topbar">
              <div>
                <h2>Document Q&amp;A</h2>
                <div className="sub">Financial document search with exact source citations</div>
              </div>
              <span className="pill">SQLite Vector + BM25</span>
            </div>

            <div className="chatlayout">
              <div className="card uploadcol">
                <h3>Indexed Documents</h3>
                <div className="sub" style={{ marginBottom: "14px" }}>
                  Upload PDF invoices or statements to query them with citations.
                </div>

                <div
                  className={`dropzone ${isDragging ? "dragging" : ""} ${uploading ? "uploading" : ""}`}
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
                    if (file) handleFileUpload(file);
                  }}
                  onClick={() => !uploading && fileInputRef.current?.click()}
                  style={{ cursor: uploading ? "default" : "pointer" }}
                >
                  <input
                    ref={fileInputRef}
                    type="file"
                    accept=".pdf,application/pdf"
                    style={{ display: "none" }}
                    onChange={(e) => {
                      const file = e.target.files?.[0];
                      if (file) handleFileUpload(file);
                      e.target.value = "";
                    }}
                  />
                  <div className="dropicon">📄</div>
                  <div className="dropprompt">
                    {uploading ? (
                      <span>Indexing document…</span>
                    ) : (
                      <>
                        <strong>Drop a PDF here</strong> or click to browse
                      </>
                    )}
                  </div>
                  <div className="dropsub">Maximum file size 10 MB</div>
                </div>

                {uploadSuccess && <div className="banner success">{uploadSuccess}</div>}
                {uploadError && <div className="banner error">{uploadError}</div>}

                <div className="doclist">
                  <div className="doclist-title">Currently Indexed ({documents.length})</div>
                  {documents.length === 0 ? (
                    <div className="docempty">No documents uploaded yet.</div>
                  ) : (
                    <div className="docitems">
                      {documents.map((d, i) => (
                        <div key={i} className="docitem">
                          <span className="docname" title={d.filename}>
                            {d.filename}
                          </span>
                          <span className="docmeta">
                            {d.chunks} chunk{d.chunks === 1 ? "" : "s"}
                          </span>
                          <button
                            type="button"
                            className="docdelete-btn"
                            disabled={deletingFile === d.filename}
                            onClick={() => handleDeleteDocument(d.filename)}
                            title={`Remove ${d.filename}`}
                            aria-label={`Remove ${d.filename}`}
                          >
                            {deletingFile === d.filename ? "…" : "✕"}
                          </button>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>

              <div className="card chatwrap">
                {hasSampleInvoices && (
                  <div className="suggest">
                    <button
                      type="button"
                      disabled={typing}
                      onClick={() => sendChat("What is the total amount of invoice INV-1042?")}
                    >
                      What is the total amount of invoice INV-1042?
                    </button>
                    <button
                      type="button"
                      disabled={typing}
                      onClick={() => sendChat("Who supplied the office notebooks?")}
                    >
                      Who supplied the office notebooks?
                    </button>
                    <button
                      type="button"
                      disabled={typing}
                      onClick={() => sendChat("What is the payment due date for BlueSky Office Supplies?")}
                    >
                      What is the payment due date for BlueSky Office Supplies?
                    </button>
                  </div>
                )}
                <div className="chatlog">
                  {chatLog.map((m, i) => (
                    <div key={i} className={`msg ${m.role === "user" ? "user" : "bot"}`}>
                      <div>{m.text}</div>
                      {m.sources && m.sources.length > 0 && (
                        <span className="cite">Source: {m.sources.join(" · ")}</span>
                      )}
                    </div>
                  ))}
                  {typing && <div className="loading">FinPilot is thinking…</div>}
                </div>
                <div className="chatinput">
                  <input
                    value={chatInput}
                    disabled={typing}
                    onChange={(e) => setChatInput(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === "Enter" && !typing && chatInput.trim()) {
                        sendChat();
                      }
                    }}
                    placeholder="Ask about an invoice or statement…"
                  />
                  <button
                    className="btn primary"
                    style={{ width: "auto" }}
                    disabled={typing || !chatInput.trim()}
                    onClick={() => sendChat()}
                  >
                    Send
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}

        {tab === "notifications" && (
          <NotificationsTab
            onOpenApproval={setActiveApprovalAction}
            onNavigateTab={setTab}
            onRefreshCount={refreshUnread}
          />
        )}

        {tab === "reports" && (
          <ReportsTab onOpenApproval={setActiveApprovalAction} />
        )}

        {tab === "agent" && (
          <AgentActivityTab
            session={session}
            onOpenApproval={setActiveApprovalAction}
            onRefreshCount={refreshUnread}
            onNavigateTab={setTab}
          />
        )}

        {/* Global Modal Approval Dialog */}
        {activeApprovalAction && (
          <ApprovalDialog
            action={activeApprovalAction}
            onClose={() => setActiveApprovalAction(null)}
            onSuccess={() => {
              refreshUnread();
              getAgentActions().then(setActions).catch(() => {});
            }}
            onGoToSettings={() => setTab("agent")}
          />
        )}
      </main>
    </div>
  );
}
