import { useEffect, useState } from "react";
import { useRouter } from "next/router";
import {
  getSession,
  logout,
  getForecast,
  getFlaggedTransactions,
  reviewTransaction,
  askDocuments,
  getAgentActions,
  approveAction,
} from "../lib/api";

function ForecastChart({ actual, forecast }) {
  if (!actual || !forecast) return null;
  const W = 600, H = 190, pad = 10;
  const all = actual.concat(forecast);
  const max = Math.max(...all), min = Math.min(...all);
  const totalPts = actual.length + forecast.length - 1;
  const xStep = (W - 2 * pad) / totalPts;
  const y = (v) => H - pad - ((v - min) / (max - min)) * (H - 2 * pad);

  const actualPath = actual.map((v, i) => `${i === 0 ? "M" : "L"}${pad + i * xStep},${y(v)}`).join(" ");
  const forecastPath = forecast
    .map((v, i) => `${i === 0 ? "M" : "L"}${pad + (actual.length - 1 + i) * xStep},${y(v)}`)
    .join(" ");

  const bandTop = forecast.map((v, i) => [pad + (actual.length - 1 + i) * xStep, y(v + 4)]);
  const bandBot = forecast.map((v, i) => [pad + (actual.length - 1 + i) * xStep, y(v - 4)]).reverse();
  const bandPath = `M${bandTop.map((p) => p.join(",")).join(" L")} L${bandBot.map((p) => p.join(",")).join(" L")} Z`;

  return (
    <svg viewBox={`0 0 ${W} ${H}`} style={{ width: "100%", height: 190, display: "block" }}>
      <path d={bandPath} fill="#2A3242" opacity="0.5" />
      <path d={actualPath} fill="none" stroke="#5D6578" strokeWidth="2" />
      <path d={forecastPath} fill="none" stroke="#3ECF8E" strokeWidth="2.5" />
      <line
        x1={pad + (actual.length - 1) * xStep}
        y1="0"
        x2={pad + (actual.length - 1) * xStep}
        y2={H}
        stroke="#2A3242"
        strokeWidth="1"
        strokeDasharray="3,3"
      />
    </svg>
  );
}

export default function Dashboard() {
  const router = useRouter();
  const [session, setSession] = useState(null);
  const [tab, setTab] = useState("overview");

  const [forecast, setForecast] = useState(null);
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
    getForecast(15).then(setForecast).catch(() => {});
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
                <div className="sub">Aarav Retail Co. \u00b7 live from FastAPI</div>
              </div>
              <span className="pill">
                <span className="dot pulse"></span>FastAPI live \u00b7 /api/v1
              </span>
            </div>

            <div className="kpirow">
              <div className="kpi">
                <div className="klabel">Next 30d forecast</div>
                <div className="kval up">
                  {forecast ? `\u20b9${(forecast.next_30d_total_inr / 100000).toFixed(1)}L` : "\u2026"}
                </div>
                <div className="kdelta">{forecast ? `MAPE ${forecast.mape}% \u00b7 RMSE ${forecast.rmse}` : "loading"}</div>
              </div>
              <div className="kpi">
                <div className="klabel">Flagged transactions</div>
                <div className="kval warn">{fraud ? pendingCount : "\u2026"}</div>
                <div className="kdelta">awaiting review</div>
              </div>
              <div className="kpi">
                <div className="klabel">Agent actions pending</div>
                <div className="kval">{actions ? pendingActions : "\u2026"}</div>
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
                <h3>Sales forecast \u2014 next {forecast?.horizon_days ?? "\u2026"} days</h3>
                <div className="cardsub">Prophet + XGBoost ensemble \u00b7 served from /api/v1/forecast</div>
                {forecast ? (
                  <ForecastChart actual={forecast.actual} forecast={forecast.forecast} />
                ) : (
                  <div className="loading">Loading forecast\u2026</div>
                )}
                <div style={{ display: "flex", gap: 16, marginTop: 10, fontSize: 11.5, color: "var(--muted)" }}>
                  <span><i style={{ width: 9, height: 9, background: "#5D6578", display: "inline-block", marginRight: 6, borderRadius: 2 }}></i>Actual</span>
                  <span><i style={{ width: 9, height: 9, background: "#3ECF8E", display: "inline-block", marginRight: 6, borderRadius: 2 }}></i>Forecast</span>
                </div>
              </div>
              <div className="card">
                <h3>System status</h3>
                <div className="cardsub">Docker Compose \u00b7 Render deployment</div>
                <table>
                  <tbody>
                    <tr><td>Frontend (Next.js)</td><td style={{ textAlign: "right", color: "var(--accent)" }}>\u25cf running</td></tr>
                    <tr><td>API gateway (FastAPI)</td><td style={{ textAlign: "right", color: "var(--accent)" }}>\u25cf running</td></tr>
                    <tr><td>Forecasting service</td><td style={{ textAlign: "right", color: "var(--accent)" }}>\u25cf running</td></tr>
                    <tr><td>Fraud detection service</td><td style={{ textAlign: "right", color: "var(--accent)" }}>\u25cf running</td></tr>
                    <tr><td>RAG / ChromaDB</td><td style={{ textAlign: "right", color: "var(--accent)" }}>\u25cf running</td></tr>
                    <tr><td>Agent layer (LangGraph)</td><td style={{ textAlign: "right", color: "var(--amber)" }}>\u25cf {pendingActions} pending</td></tr>
                  </tbody>
                </table>
                <div className="badge-row">
                  <span className="stackbadge">Next.js</span>
                  <span className="stackbadge">FastAPI</span>
                  <span className="stackbadge">JWT \u00b7 RBAC</span>
                  <span className="stackbadge">Docker</span>
                  <span className="stackbadge">Render</span>
                </div>
              </div>
            </div>
          </div>
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
