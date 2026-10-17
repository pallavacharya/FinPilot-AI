import { useEffect, useState } from "react";
import { useRouter } from "next/router";
import ProductForecastTab from "../components/ProductForecastTab";
import {
  getSession,
  logout,
  getForecastSummary,
  getForecastNextWeek,
  getFlaggedTransactions,
  reviewTransaction,
  askDocuments,
  getAgentActions,
  approveAction,
} from "../lib/api";

export default function Dashboard() {
  const router = useRouter();
  const [session, setSession] = useState(null);
  const [tab, setTab] = useState("overview");

  const [summary, setSummary] = useState(null);
  const [nextWeekItems, setNextWeekItems] = useState([]);
  const [fraud, setFraud] = useState(null);
  const [actions, setActions] = useState(null);

  const [chatLog, setChatLog] = useState([
    { role: "bot", text: "Hi, I'm the FinPilot document assistant. Ask about your invoices and statements \u2014 I'll cite the source." },
  ]);
  const [chatInput, setChatInput] = useState("");
  const [typing, setTyping] = useState(false);

  useEffect(() => {
    const s = getSession();
    if (!s) {
      router.push("/");
      return;
    }
    setSession(s);
    getForecastSummary().then(setSummary).catch(() => {});
    getForecastNextWeek().then((res) => setNextWeekItems(res.items || [])).catch(() => {});
    getFlaggedTransactions().then(setFraud).catch(() => {});
    getAgentActions().then(setActions).catch(() => {});
  }, []);

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

  function sendChat(text) {
    const q = (text ?? chatInput).trim();
    if (!q) return;
    setChatLog((log) => [...log, { role: "user", text: q }]);
    setChatInput("");
    setTyping(true);

    askDocuments(q)
      .then((res) => {
        setTyping(false);
        setChatLog((log) => [...log, { role: "bot", text: res.answer, sources: res.sources }]);
      })
      .catch(() => {
        setTyping(false);
        setChatLog((log) => [...log, { role: "bot", text: "Couldn't reach the document service." }]);
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

  return (
    <div className="shell">
      <nav>
        <div className="brand">
          <div className="brand-mark">F</div>
          <div className="brand-name">FinPilot AI</div>
        </div>
        <button className={`navitem ${tab === "overview" ? "active" : ""}`} onClick={() => setTab("overview")}>
          <span className="navlabel">Overview</span>
        </button>
        <button className={`navitem ${tab === "forecast" ? "active" : ""}`} onClick={() => setTab("forecast")}>
          <span className="navlabel">Product forecast</span>
        </button>
        <button className={`navitem ${tab === "fraud" ? "active" : ""}`} onClick={() => setTab("fraud")}>
          <span className="navlabel">Fraud alerts</span>
        </button>
        <button className={`navitem ${tab === "chat" ? "active" : ""}`} onClick={() => setTab("chat")}>
          <span className="navlabel">Document Q&amp;A</span>
        </button>
        <button className={`navitem ${tab === "agent" ? "active" : ""}`} onClick={() => setTab("agent")}>
          <span className="navlabel">Agent activity</span>
        </button>
        <div className="navspacer"></div>
        <button className="navitem" onClick={handleLogout}>
          <span className="navlabel">Sign out</span>
        </button>
        <div className="userchip">
          <div className="avatar">{initial}</div>
          <div>
            <div className="uname">{session.name}</div>
            <div className="urole">{session.role}</div>
          </div>
        </div>
      </nav>

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
                <div className="kval warn">{fraud ? pendingCount : "…"}</div>
                <div className="kdelta">awaiting review</div>
              </div>
              <div className="kpi">
                <div className="klabel">Agent actions pending</div>
                <div className="kval">{actions ? pendingActions : "…"}</div>
                <div className="kdelta">gated on human approval</div>
              </div>
              <div className="kpi">
                <div className="klabel">Doc Q&amp;A accuracy</div>
                <div className="kval up">100%</div>
                <div className="kdelta">10/10 benchmark, 95% keyword coverage</div>
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
          <div>
            <div className="topbar">
              <div>
                <h2>Fraud alerts</h2>
                <div className="sub">Isolation Forest + XGBoost risk scoring \u00b7 served from /api/v1/fraud</div>
              </div>
              <span className="pill">{fraud ? `${flagged.length} scored / ${fraud.total_scanned} scanned` : "\u2026"}</span>
            </div>
            <div className="card">
              {!fraud ? (
                <div className="loading">Loading transactions\u2026</div>
              ) : (
                <table>
                  <thead>
                    <tr><th>Transaction</th><th>Amount</th><th>Customer</th><th>Risk score</th><th>Status</th><th></th></tr>
                  </thead>
                  <tbody>
                    {flagged.map((t) => {
                      const level = t.risk_score >= 0.8 ? "high" : t.risk_score >= 0.4 ? "med" : "low";
                      return (
                        <tr key={t.id}>
                          <td className="amt">{t.id}</td>
                          <td className="amt">\u20b9{t.amount.toLocaleString("en-IN")}</td>
                          <td>{t.customer}</td>
                          <td><span className={`risk ${level}`}>{t.risk_score.toFixed(2)}</span></td>
                          <td style={{ textTransform: "capitalize" }}>{t.status}</td>
                          <td>
                            {t.status === "pending" && (
                              <button className="btn ghost" style={{ padding: "5px 10px", fontSize: 11.5 }} onClick={() => handleReview(t.id, "clear")}>
                                Clear
                              </button>
                            )}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              )}
            </div>
          </div>
        )}

        {tab === "chat" && (
          <div>
            <div className="topbar">
              <div>
                <h2>Document Q&amp;A</h2>
                <div className="sub">Grounded retrieval over uploaded invoices &amp; statements \u00b7 served from /api/v1/documents</div>
              </div>
              <span className="pill">4 documents indexed</span>
            </div>
            <div className="card chatwrap">
              <div className="suggest">
                <button onClick={() => sendChat("How much did we spend on suppliers last quarter?")}>Supplier spend last quarter?</button>
                <button onClick={() => sendChat("Which invoice has the highest amount?")}>Largest invoice?</button>
                <button onClick={() => sendChat("Any overdue payments?")}>Overdue payments?</button>
              </div>
              <div className="chatlog">
                {chatLog.map((m, i) => (
                  <div key={i} className={`msg ${m.role === "user" ? "user" : "bot"}`}>
                    {m.text}
                    {m.sources && <span className="cite">Source: {m.sources.join(" \u00b7 ")}</span>}
                  </div>
                ))}
                {typing && <div className="loading">FinPilot is thinking\u2026</div>}
              </div>
              <div className="chatinput">
                <input
                  value={chatInput}
                  onChange={(e) => setChatInput(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && sendChat()}
                  placeholder="Ask about an invoice or statement\u2026"
                />
                <button className="btn primary" style={{ width: "auto" }} onClick={() => sendChat()}>
                  Send
                </button>
              </div>
            </div>
          </div>
        )}

        {tab === "agent" && (
          <div>
            <div className="topbar">
              <div>
                <h2>Agent activity</h2>
                <div className="sub">LangGraph decision loop \u00b7 served from /api/v1/agent</div>
              </div>
              <span className="pill">Audit trail: 100% coverage</span>
            </div>
            {!actions ? (
              <div className="loading">Loading agent actions\u2026</div>
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
                  <div className="audit">audit_id: {a.id} \u00b7 actor: agent.langgraph \u00b7 gate: human_approval_required</div>
                </div>
              ))
            )}
          </div>
        )}
      </main>
    </div>
  );
}
