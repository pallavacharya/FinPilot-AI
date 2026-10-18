import { useEffect, useState, useRef } from "react";
import { useRouter } from "next/router";
import ProductForecastTab from "../components/ProductForecastTab";
import Sidebar from "../components/Sidebar";
import FraudTab from "../components/FraudTab";
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
  }, []);

  useEffect(() => {
    if (tab === "chat") {
      loadDocuments();
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

  async function handleApprove(id) {
    await approveAction(id);
    getAgentActions().then(setActions);
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

  const initial = session.name ? session.name[0] : "U";
  const flagged = fraud?.transactions ?? [];
  const pendingCount = flagged.filter((t) => t.status === "pending").length;
  const pendingActions = (actions?.actions ?? []).filter((a) => a.status !== "executed").length;

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
      />

      <main>
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
                <div className="klabel">Flagged transactions</div>
                <div className="kval warn">{fraud ? (fraud.count ?? pendingCount) : "…"}</div>
                <div className="kdelta">suspicious across all uploads</div>
              </div>
              <div className="kpi">
                <div className="klabel">Agent actions pending</div>
                <div className="kval">{actions ? pendingActions : "…"}</div>
                <div className="kdelta">gated on human approval</div>
              </div>
              <div className="kpi">
                <div className="klabel">Retrieval check</div>
                <div className={`kval ${evalSummary ? "up" : ""}`}>
                  {evalSummary ? `${evalSummary.passed}/${evalSummary.total}` : "-"}
                </div>
                {evalSummary && (
                  <div className="kdelta">
                    right source retrieved ({evalSummary.documents_in_eval} sample invoices)
                  </div>
                )}
              </div>
            </div>

            <div className="grid">
              <div className="card">
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 12 }}>
                  <div>
                    <h3>Next week by sub-category</h3>
                    <div className="cardsub" style={{ marginBottom: 0 }}>Top 8 products by predicted sales</div>
                  </div>
                  <span className="pill" style={{ fontSize: 10.5 }}>Superstore US$</span>
                </div>

                {nextWeekItems.length === 0 ? (
                  <div className="loading">Loading forecast…</div>
                ) : (
                  <div style={{ display: "flex", flexDirection: "column", gap: 10, marginTop: 10 }}>
                    {top8Items.map((item) => {
                      const pct = Math.max(8, Math.min(100, (item.predicted_sales / maxTop8) * 100));
                      return (
                        <div key={item.sub_category}>
                          <div style={{ display: "flex", justifyContent: "space-between", fontSize: 12.5, marginBottom: 4 }}>
                            <span style={{ fontWeight: 500 }}>{item.sub_category}</span>
                            <span className="amt" style={{ color: "var(--accent)" }}>
                              ${Number(item.predicted_sales).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                            </span>
                          </div>
                          <div style={{ height: 6, background: "var(--panel-2)", borderRadius: 3, overflow: "hidden" }}>
                            <div style={{ width: `${pct}%`, height: "100%", background: "var(--accent)", borderRadius: 3 }}></div>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                )}

                <button
                  className="btn ghost"
                  style={{ marginTop: 16, width: "100%", fontSize: 12.5, display: "flex", alignItems: "center", justifyContent: "center", gap: 6 }}
                  onClick={() => setTab("forecast")}
                >
                  Open product forecast <span>→</span>
                </button>
              </div>

              <div className="card">
                <h3>System status</h3>
                <div className="cardsub">Docker Compose · Render deployment</div>
                <table>
                  <tbody>
                    <tr><td>Frontend (Next.js)</td><td style={{ textAlign: "right", color: "var(--accent)" }}>● running</td></tr>
                    <tr><td>API gateway (FastAPI)</td><td style={{ textAlign: "right", color: "var(--accent)" }}>● running</td></tr>
                    <tr><td>Forecasting service</td><td style={{ textAlign: "right", color: "var(--accent)" }}>● running</td></tr>
                    <tr><td>Fraud detection service</td><td style={{ textAlign: "right", color: "var(--accent)" }}>● running</td></tr>
                    <tr><td>RAG / ChromaDB</td><td style={{ textAlign: "right", color: "var(--accent)" }}>● running</td></tr>
                    <tr><td>Agent layer (LangGraph)</td><td style={{ textAlign: "right", color: "var(--amber)" }}>● {pendingActions} pending</td></tr>
                  </tbody>
                </table>
                <div className="badge-row">
                  <span className="stackbadge">Next.js</span>
                  <span className="stackbadge">FastAPI</span>
                  <span className="stackbadge">JWT · RBAC</span>
                  <span className="stackbadge">Docker</span>
                  <span className="stackbadge">Render</span>
                </div>
              </div>
            </div>
          </div>
        )}

        {tab === "forecast" && (
          <ProductForecastTab />
        )}

        {tab === "fraud" && (
          <FraudTab
            session={session}
            onHistoryChange={() => {
              getFlaggedTransactions().then(setFraud).catch(() => {});
            }}
          />
        )}

        {tab === "chat" && (
          <div>
            <div className="topbar">
              <div>
                <h2>Document Q&amp;A</h2>
                <div className="sub">Grounded retrieval over uploaded invoices &amp; statements · served from /api/v1/documents</div>
              </div>
              <span className="pill">
                {documents.length === 0
                  ? "No documents yet"
                  : `${documents.length} document${documents.length === 1 ? "" : "s"} indexed`}
              </span>
            </div>

            <div className="doc-layout">
              <div className="card doc-panel">
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline" }}>
                  <h3 style={{ margin: 0 }}>Indexed documents</h3>
                  <span className="pill" style={{ fontSize: 10.5 }}>
                    {documents.length} {documents.length === 1 ? "file" : "files"}
                  </span>
                </div>
                <div className="cardsub" style={{ marginBottom: 4 }}>PDFs indexed for grounding</div>

                <div
                  className={`upload-zone ${isDragging ? "dragging" : ""}`}
                  onDragOver={(e) => {
                    e.preventDefault();
                    setIsDragging(true);
                  }}
                  onDragLeave={() => setIsDragging(false)}
                  onDrop={(e) => {
                    e.preventDefault();
                    setIsDragging(false);
                    const file = e.dataTransfer.files?.[0];
                    if (file) handleFileUpload(file);
                  }}
                >
                  <input
                    ref={fileInputRef}
                    type="file"
                    accept=".pdf,application/pdf"
                    style={{ display: "none" }}
                    onChange={(e) => {
                      const f = e.target.files?.[0];
                      if (f) handleFileUpload(f);
                      e.target.value = "";
                    }}
                  />
                  <button
                    type="button"
                    className="btn primary"
                    disabled={uploading}
                    onClick={() => fileInputRef.current?.click()}
                  >
                    {uploading ? "Indexing…" : "Upload PDF"}
                  </button>
                  <div className="upload-hint">Drop a PDF here or click to upload (max 10 MB)</div>
                </div>

                {uploadSuccess && (
                  <div className="upload-status success">
                    {uploadSuccess}
                  </div>
                )}
                {uploadError && (
                  <div className="upload-status error">
                    {uploadError}
                  </div>
                )}

                <div className="doc-list-wrap">
                  {documents.length === 0 ? (
                    <div className="doc-empty">
                      Upload a PDF invoice to start asking questions.
                    </div>
                  ) : (
                    <div className="doc-list">
                      {documents.map((d) => (
                        <div key={d.filename} className="doc-item">
                          <span className="doc-badge">PDF</span>
                          <div className="doc-meta">
                            <div className="doc-name" title={d.filename}>{d.filename}</div>
                            <div className="doc-sub">
                              {d.pages} {d.pages === 1 ? "page" : "pages"} · {d.chunks} {d.chunks === 1 ? "chunk" : "chunks"}
                            </div>
                          </div>
                          <button
                            type="button"
                            className="doc-del-btn"
                            title={`Remove ${d.filename}`}
                            disabled={deletingFile === d.filename}
                            onClick={() => handleDeleteDocument(d.filename)}
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

        {tab === "agent" && (
          <div>
            <div className="topbar">
              <div>
                <h2>Agent activity</h2>
                <div className="sub">LangGraph decision loop · served from /api/v1/agent</div>
              </div>
              <span className="pill">Audit trail: 100% coverage</span>
            </div>
            {!actions ? (
              <div className="loading">Loading agent actions…</div>
            ) : (
              actions.actions.map((a) => (
                <div key={a.id} className={`agentcard ${a.status === "executed" ? "approved" : ""}`}>
                  <div className="agenthead">
                    <div className="atitle">{a.title}</div>
                  </div>
                  <div className="agentbody">{a.body}</div>
                  <div className="agentactions">
                    {a.status === "executed" ? (
                      <span className="status-approved"><span className="dot"></span>Approved &amp; executed</span>
                    ) : (
                      <button className="btn primary" style={{ width: "auto" }} onClick={() => handleApprove(a.id)}>
                        Approve
                      </button>
                    )}
                  </div>
                  <div className="audit">audit_id: {a.id} · actor: agent.langgraph · gate: human_approval_required</div>
                </div>
              ))
            )}
          </div>
        )}
      </main>
    </div>
  );
}
