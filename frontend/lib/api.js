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

export async function uploadForecastCsv(file) {
  const formData = new FormData();
  formData.append("file", file);
  const token = typeof window !== "undefined" ? localStorage.getItem("finpilot_token") : null;
  const headers = {};
  if (token) headers["Authorization"] = `Bearer ${token}`;

  const res = await fetch(`${API_BASE}/forecast/upload`, {
    method: "POST",
    headers,
    body: formData,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Failed to upload and update forecast CSV");
  }
  return res.json();
}

export async function resetForecast() {
  const res = await fetch(`${API_BASE}/forecast/reset`, {
    method: "POST",
    headers: authHeaders(),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Failed to reset forecast");
  }
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

export async function uploadFraudCsv(file) {
  const formData = new FormData();
  formData.append("file", file);
  const res = await fetch(`${API_BASE}/fraud/upload`, {
    method: "POST",
    headers: authHeaders(),
    body: formData,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Failed to upload and score CSV");
  }
  return res.json();
}

export async function getFraudHistory() {
  const res = await fetch(`${API_BASE}/fraud/history`, { headers: authHeaders() });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Failed to load fraud history");
  }
  return res.json();
}

export async function clearFraudHistory() {
  const res = await fetch(`${API_BASE}/fraud/history`, {
    method: "DELETE",
    headers: authHeaders(),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Failed to clear fraud history");
  }
  return res.json();
}


export async function askDocuments(question) {
  const res = await fetch(`${API_BASE}/documents/ask`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify({ question }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Request failed");
  }
  return res.json();
}

export async function uploadDocument(file) {
  const formData = new FormData();
  formData.append("file", file);
  const res = await fetch(`${API_BASE}/documents/upload`, {
    method: "POST",
    headers: authHeaders(),
    body: formData,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Request failed");
  }
  return res.json();
}

export async function listDocuments() {
  const res = await fetch(`${API_BASE}/documents/list`, {
    headers: authHeaders(),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Request failed");
  }
  return res.json();
}

export async function getDocumentEvalSummary() {
  const res = await fetch(`${API_BASE}/documents/eval-summary`, {
    headers: authHeaders(),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Request failed");
  }
  return res.json();
}

export async function deleteDocument(filename) {
  const res = await fetch(`${API_BASE}/documents/${encodeURIComponent(filename)}`, {
    method: "DELETE",
    headers: authHeaders(),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Failed to delete document");
  }
  return res.json();
}



export async function getAgentActions() {
  const res = await fetch(`${API_BASE}/agent/actions`, { headers: authHeaders() });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Failed to load agent actions");
  }
  return res.json();
}

export async function approveAction(actionId) {
  const res = await fetch(`${API_BASE}/agent/actions/approve`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify({ action_id: actionId }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Approval failed");
  }
  return res.json();
}

export async function rejectAction(actionId, reason = "") {
  const res = await fetch(`${API_BASE}/agent/actions/reject`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify({ action_id: actionId, reason }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Rejection failed");
  }
  return res.json();
}

export async function runAgentChecks() {
  const res = await fetch(`${API_BASE}/agent/run-checks`, {
    method: "POST",
    headers: authHeaders(),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Failed to run checks");
  }
  return res.json();
}

export async function getNotifications(unreadOnly = false, limit = 200) {
  const res = await fetch(`${API_BASE}/agent/notifications?unread_only=${unreadOnly}&limit=${limit}`, {
    headers: authHeaders(),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Failed to load notifications");
  }
  return res.json();
}

export async function getUnreadNotificationCount() {
  const res = await fetch(`${API_BASE}/agent/notifications/unread-count`, {
    headers: authHeaders(),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Failed to load unread count");
  }
  return res.json();
}

export async function markNotificationsRead({ ids = null, all = false } = {}) {
  const res = await fetch(`${API_BASE}/agent/notifications/read`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify({ ids, all }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Failed to mark notifications read");
  }
  return res.json();
}

export async function getReports(kind = null, limit = 100) {
  const query = new URLSearchParams();
  if (kind) query.set("kind", kind);
  query.set("limit", String(limit));
  const res = await fetch(`${API_BASE}/agent/reports?${query.toString()}`, {
    headers: authHeaders(),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Failed to load reports");
  }
  return res.json();
}

export async function getReportById(reportId) {
  const res = await fetch(`${API_BASE}/agent/reports/${encodeURIComponent(reportId)}`, {
    headers: authHeaders(),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Failed to load report");
  }
  return res.json();
}

export async function generateReport(kind, scope = "newest", batchId = null) {
  const res = await fetch(`${API_BASE}/agent/reports/generate`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify({ kind, scope, batch_id: batchId }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Failed to generate report");
  }
  return res.json();
}

export async function getAuditLog(limit = 100, event = null) {
  const query = new URLSearchParams();
  query.set("limit", String(limit));
  if (event) query.set("event", event);
  const res = await fetch(`${API_BASE}/agent/audit?${query.toString()}`, {
    headers: authHeaders(),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Failed to load audit log");
  }
  return res.json();
}

export async function getAgentSettings() {
  const res = await fetch(`${API_BASE}/agent/settings`, {
    headers: authHeaders(),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Failed to load settings");
  }
  return res.json();
}

export async function updateAgentSettings(payload) {
  const res = await fetch(`${API_BASE}/agent/settings`, {
    method: "PUT",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Failed to update settings");
  }
  return res.json();
}

export async function sendTestEmail() {
  const res = await fetch(`${API_BASE}/agent/settings/test-email`, {
    method: "POST",
    headers: authHeaders(),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Failed to send test email");
  }
  return res.json();
}
