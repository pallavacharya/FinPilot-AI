import React, { useState, useEffect } from "react";
import { getNotifications, markNotificationsRead, getAgentActions } from "../lib/api";
import {
  IconFraud,
  IconUsers,
  IconTrendingDown,
  IconMail,
  IconClock,
  IconInfo,
  IconCheck,
  IconBell,
} from "./icons";

function formatRelativeTime(isoString) {
  if (!isoString) return "";
  try {
    const d = new Date(isoString);
    const now = new Date();
    const diffSec = Math.floor((now - d) / 1000);
    if (diffSec < 60) return "Just now";
    const diffMin = Math.floor(diffSec / 60);
    if (diffMin < 60) return `${diffMin}m ago`;
    const diffHour = Math.floor(diffMin / 60);
    if (diffHour < 24) return `${diffHour}h ago`;
    const diffDay = Math.floor(diffHour / 24);
    if (diffDay < 7) return `${diffDay}d ago`;
    return d.toLocaleDateString("en-US", { month: "short", day: "numeric" });
  } catch (e) {
    return isoString;
  }
}

function isToday(isoString) {
  if (!isoString) return false;
  try {
    const d = new Date(isoString);
    const now = new Date();
    return (
      d.getDate() === now.getDate() &&
      d.getMonth() === now.getMonth() &&
      d.getFullYear() === now.getFullYear()
    );
  } catch (e) {
    return false;
  }
}

export default function NotificationsTab({
  onOpenApproval,
  onNavigateTab,
  onRefreshCount,
}) {
  const [notifications, setNotifications] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState("all"); // 'all' | 'unread'
  const [actionsMap, setActionsMap] = useState({});

  function loadData() {
    setLoading(true);
    Promise.all([
      getNotifications(false, 200).catch(() => ({ notifications: [] })),
      getAgentActions().catch(() => ({ actions: [] })),
    ]).then(([nData, aData]) => {
      setNotifications(nData.notifications || []);
      const aMap = {};
      (aData.actions || []).forEach((a) => {
        aMap[a.id] = a;
      });
      setActionsMap(aMap);
      setLoading(false);
    });
  }

  useEffect(() => {
    loadData();
  }, []);

  async function handleMarkAllRead() {
    try {
      await markNotificationsRead({ all: true });
      setNotifications((prev) => prev.map((n) => ({ ...n, read: true })));
      if (onRefreshCount) onRefreshCount();
    } catch (e) {
      console.error("Failed to mark all read", e);
    }
  }

  async function handleRowClick(n) {
    if (!n.read) {
      try {
        await markNotificationsRead({ ids: [n.id] });
        setNotifications((prev) =>
          prev.map((item) => (item.id === n.id ? { ...item, read: true } : item))
        );
        if (onRefreshCount) onRefreshCount();
      } catch (e) {
        console.error("Failed to mark notification read", e);
      }
    }
  }

  function handleActionClick(e, n) {
    e.stopPropagation();
    handleRowClick(n);

    if (n.action_id && actionsMap[n.action_id]) {
      const act = actionsMap[n.action_id];
      if (act.status === "pending_approval" || act.status === "failed") {
        if (onOpenApproval) onOpenApproval(act);
        return;
      }
    }

    if (n.report_id) {
      if (onNavigateTab) onNavigateTab("reports");
      return;
    }

    if (onNavigateTab) onNavigateTab("agent");
  }

  const filtered = notifications.filter((n) => (filter === "unread" ? !n.read : true));
  const todayList = filtered.filter((n) => isToday(n.created_at));
  const earlierList = filtered.filter((n) => !isToday(n.created_at));

  function renderIcon(type) {
    switch (type) {
      case "fraud_alert":
        return <IconFraud size={18} style={{ color: "var(--red)" }} />;
      case "repeat_offender":
        return <IconUsers size={18} style={{ color: "var(--amber)" }} />;
      case "forecast_drop":
        return <IconTrendingDown size={18} style={{ color: "var(--amber)" }} />;
      case "report_sent":
        return <IconMail size={18} style={{ color: "var(--accent)" }} />;
      case "reminder":
        return <IconClock size={18} style={{ color: "var(--amber)" }} />;
      case "info":
      default:
        return <IconInfo size={18} style={{ color: "var(--muted)" }} />;
    }
  }

  function renderGroup(title, items) {
    if (items.length === 0) return null;
    return (
      <div style={{ marginBottom: "24px" }}>
        <div
          style={{
            fontSize: "12px",
            fontWeight: 700,
            textTransform: "uppercase",
            letterSpacing: "0.06em",
            color: "var(--faint)",
            marginBottom: "10px",
            paddingLeft: "4px",
          }}
        >
          {title} ({items.length})
        </div>
        <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
          {items.map((n) => {
            const hasAction = Boolean(n.action_id && actionsMap[n.action_id]);
            const actionStatus = hasAction ? actionsMap[n.action_id].status : null;
            const canApprove = actionStatus === "pending_approval" || actionStatus === "failed";

            return (
              <div
                key={n.id}
                onClick={() => handleRowClick(n)}
                className={`notif-card ${!n.read ? "unread" : ""}`}
                style={{
                  background: !n.read ? "var(--panel-2)" : "var(--panel)",
                  border: "1px solid var(--border)",
                  borderRadius: "10px",
                  padding: "14px 16px",
                  display: "flex",
                  alignItems: "flex-start",
                  gap: "14px",
                  cursor: "pointer",
                  transition: "background 0.15s, border-color 0.15s",
                  position: "relative",
                }}
              >
                {/* Type icon box */}
                <div
                  style={{
                    width: "36px",
                    height: "36px",
                    borderRadius: "8px",
                    background: "rgba(0,0,0,0.25)",
                    border: "1px solid var(--border)",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    flexShrink: 0,
                    marginTop: "2px",
                  }}
                >
                  {renderIcon(n.type)}
                </div>

                {/* Content */}
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: "8px", marginBottom: "4px" }}>
                    <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                      <span style={{ fontSize: "14px", fontWeight: 600, color: "var(--text)" }}>
                        {n.title}
                      </span>
                      {!n.read && (
                        <span
                          style={{
                            width: "7px",
                            height: "7px",
                            borderRadius: "50%",
                            background: "var(--accent)",
                            display: "inline-block",
                          }}
                          title="Unread notification"
                        />
                      )}
                    </div>
                    <span style={{ fontSize: "11.5px", color: "var(--faint)", whiteSpace: "nowrap" }}>
                      {formatRelativeTime(n.created_at)}
                    </span>
                  </div>

                  <div style={{ fontSize: "13px", color: "var(--muted)", lineHeight: 1.5, marginBottom: "8px" }}>
                    {n.message}
                  </div>

                  {/* Context Action Button */}
                  <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                    {canApprove ? (
                      <button
                        type="button"
                        className="btn primary"
                        onClick={(e) => handleActionClick(e, n)}
                        style={{ padding: "6px 14px", fontSize: "12px", width: "auto" }}
                      >
                        Review &amp; approve
                      </button>
                    ) : n.report_id ? (
                      <button
                        type="button"
                        className="btn"
                        onClick={(e) => handleActionClick(e, n)}
                        style={{ padding: "5px 12px", fontSize: "12px" }}
                      >
                        View report
                      </button>
                    ) : (
                      <button
                        type="button"
                        className="btn ghost"
                        onClick={(e) => handleActionClick(e, n)}
                        style={{ padding: "4px 8px", fontSize: "11.5px", color: "var(--muted)" }}
                      >
                        Open Agent activity &rarr;
                      </button>
                    )}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    );
  }

  return (
    <div>
      {/* Top Header Bar */}
      <div className="topbar">
        <div>
          <h2>Notifications</h2>
          <div className="sub">Real-time alerts, approvals, and system updates</div>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
          {notifications.some((n) => !n.read) && (
            <button
              type="button"
              className="btn"
              onClick={handleMarkAllRead}
              style={{ padding: "6px 12px", fontSize: "12px", display: "flex", alignItems: "center", gap: "6px" }}
            >
              <IconCheck size={14} /> Mark all as read
            </button>
          )}
        </div>
      </div>

      {/* Filter Tabs */}
      <div style={{ display: "flex", gap: "8px", marginBottom: "18px" }}>
        <button
          type="button"
          className={`btn ${filter === "all" ? "primary" : ""}`}
          onClick={() => setFilter("all")}
          style={{ padding: "6px 14px", fontSize: "12.5px", width: "auto" }}
        >
          All ({notifications.length})
        </button>
        <button
          type="button"
          className={`btn ${filter === "unread" ? "primary" : ""}`}
          onClick={() => setFilter("unread")}
          style={{ padding: "6px 14px", fontSize: "12.5px", width: "auto" }}
        >
          Unread ({notifications.filter((n) => !n.read).length})
        </button>
      </div>

      {/* Body List */}
      {loading ? (
        <div className="loading" style={{ padding: "40px", textAlign: "center" }}>
          Loading notifications...
        </div>
      ) : filtered.length === 0 ? (
        <div className="card fraud-empty-card" style={{ padding: "60px 20px" }}>
          <div className="empty-icon-box">
            <IconBell size={28} />
          </div>
          <h3 style={{ margin: "0 0 8px 0", fontSize: "16px", color: "var(--text)" }}>
            {filter === "unread" ? "No unread notifications" : "No notifications yet"}
          </h3>
          <p className="empty-subtext">
            {filter === "unread"
              ? "You are all caught up! Switch to 'All' to review earlier notifications."
              : "Notifications generated from fraud uploads, forecast alerts, and approvals will appear here."}
          </p>
        </div>
      ) : (
        <div>
          {renderGroup("Today", todayList)}
          {renderGroup("Earlier", earlierList)}
        </div>
      )}
    </div>
  );
}
