const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000/api/v1";

function authHeaders() {
  const token = typeof window !== "undefined" ? localStorage.getItem("finpilot_token") : null;
  return token ? { Authorization: `Bearer ${token}` } : {};
}

export async function login(email, password) {
  const res = await fetch(`${API_BASE}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  if (!res.ok) throw new Error("Invalid credentials");
  const data = await res.json();
  localStorage.setItem("finpilot_token", data.access_token);
  localStorage.setItem("finpilot_role", data.role);
  localStorage.setItem("finpilot_name", data.name);
  return data;
}

export function logout() {
  localStorage.removeItem("finpilot_token");
  localStorage.removeItem("finpilot_role");
  localStorage.removeItem("finpilot_name");
}

export function getSession() {
  if (typeof window === "undefined") return null;
  const token = localStorage.getItem("finpilot_token");
  if (!token) return null;
  return {
    token,
    role: localStorage.getItem("finpilot_role"),
    name: localStorage.getItem("finpilot_name"),
  };
}

export async function getForecast(horizonDays = 30) {
  const res = await fetch(`${API_BASE}/forecast?horizon_days=${horizonDays}`, { headers: authHeaders() });
  return res.json();
}

export async function getForecastCategories() {
  const res = await fetch(`${API_BASE}/forecast/categories`, { headers: authHeaders() });
  if (!res.ok) throw new Error("Failed to load forecast categories");
  return res.json();
}

export async function getForecastNextWeek() {
  const res = await fetch(`${API_BASE}/forecast/next-week`, { headers: authHeaders() });
  if (!res.ok) throw new Error("Failed to load next week forecast");
  return res.json();
}

export async function getForecastPredict(item) {
  const res = await fetch(`${API_BASE}/forecast/predict?item=${encodeURIComponent(item)}`, { headers: authHeaders() });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Failed to predict item");
  }
  return res.json();
}

export async function getForecastChart(item) {
  const res = await fetch(`${API_BASE}/forecast/chart?item=${encodeURIComponent(item)}`, { headers: authHeaders() });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Failed to load forecast chart");
  }
  return res.json();
}

export async function getForecastSummary() {
  const res = await fetch(`${API_BASE}/forecast/summary`, { headers: authHeaders() });
  if (!res.ok) throw new Error("Failed to load forecast summary");
  return res.json();
}

export async function getFlaggedTransactions() {
  const res = await fetch(`${API_BASE}/fraud`, { headers: authHeaders() });
  return res.json();
}

export async function reviewTransaction(transactionId, decision) {
  const res = await fetch(`${API_BASE}/fraud/review`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify({ transaction_id: transactionId, decision }),
  });
  return res.json();
}

export async function askDocuments(question) {
  const res = await fetch(`${API_BASE}/documents/ask`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify({ question }),
  });
  return res.json();
}

export async function getAgentActions() {
  const res = await fetch(`${API_BASE}/agent/actions`, { headers: authHeaders() });
  return res.json();
}

export async function approveAction(actionId) {
  const res = await fetch(`${API_BASE}/agent/actions/approve`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify({ action_id: actionId }),
  });
  return res.json();
}
