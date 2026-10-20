import React from "react";
import Logo from "./Logo";
import {
  IconOverview,
  IconForecast,
  IconFraud,
  IconChat,
  IconAgent,
  IconBell,
  IconReport,
  IconSignOut,
  IconSidebarToggle,
} from "./icons";

const NAV_ITEMS = [
  { id: "overview", label: "Overview", Icon: IconOverview },
  { id: "forecast", label: "Product forecast", Icon: IconForecast },
  { id: "fraud", label: "Fraud alerts", Icon: IconFraud },
  { id: "chat", label: "Document Q&A", Icon: IconChat },
  { id: "notifications", label: "Notifications", Icon: IconBell, hasBadge: true },
  { id: "reports", label: "Reports", Icon: IconReport },
  { id: "agent", label: "Agent activity", Icon: IconAgent },
];

export default function Sidebar({
  tab,
  setTab,
  session,
  onLogout,
  collapsed,
  setCollapsed,
  unreadCount = 0,
}) {
  const initial = session?.name ? session.name[0] : "U";

  function toggleSidebar() {
    setCollapsed((prev) => {
      const next = !prev;
      try {
        localStorage.setItem("finpilot.sidebar", String(next));
      } catch (e) {}
      return next;
    });
  }

  return (
    <nav className={`sidebar ${collapsed ? "collapsed" : "expanded"}`}>
      <div className="sidebar-header">
        <div className="sidebar-brand-wrap">
          <Logo collapsed={collapsed} />
        </div>
        <button
          type="button"
          className="sidebar-toggle-btn"
          onClick={toggleSidebar}
          aria-expanded={!collapsed}
          aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
          title={collapsed ? "Expand sidebar" : "Collapse sidebar"}
        >
          <IconSidebarToggle collapsed={collapsed} />
        </button>
      </div>

      <div className="nav-items-list">
        {NAV_ITEMS.map(({ id, label, Icon, hasBadge }) => {
          const isActive = tab === id;
          const showBadge = hasBadge && unreadCount > 0;
          return (
            <button
              key={id}
              type="button"
              className={`navitem ${isActive ? "active" : ""}`}
              onClick={() => setTab(id)}
              aria-label={showBadge ? `${label}, ${unreadCount} unread` : label}
              title={collapsed ? label : undefined}
            >
              <span className="navicon" style={{ position: "relative" }}>
                <Icon size={20} />
                {collapsed && showBadge && (
                  <span
                    style={{
                      position: "absolute",
                      top: "-2px",
                      right: "-3px",
                      width: "7px",
                      height: "7px",
                      borderRadius: "50%",
                      background: "var(--accent)",
                    }}
                  />
                )}
              </span>
              {!collapsed && <span className="navlabel">{label}</span>}
              {!collapsed && showBadge && (
                <span
                  style={{
                    marginLeft: "auto",
                    background: "var(--accent)",
                    color: "#08120D",
                    fontSize: "10.5px",
                    fontWeight: 800,
                    padding: "1px 6px",
                    borderRadius: "10px",
                    lineHeight: 1.4,
                  }}
                >
                  {unreadCount > 9 ? "9+" : unreadCount}
                </span>
              )}
              {collapsed && (
                <span className="sidebar-tooltip">
                  {label} {showBadge ? `(${unreadCount > 9 ? "9+" : unreadCount})` : ""}
                </span>
              )}
            </button>
          );
        })}
      </div>

      <div className="navspacer" />

      <button
        type="button"
        className="navitem signout-btn"
        onClick={onLogout}
        aria-label="Sign out"
        title={collapsed ? "Sign out" : undefined}
      >
        <span className="navicon">
          <IconSignOut size={20} />
        </span>
        {!collapsed && <span className="navlabel">Sign out</span>}
        {collapsed && <span className="sidebar-tooltip">Sign out</span>}
      </button>

      {session && (
        <div className="userchip" title={collapsed ? `${session.name} (${session.role})` : undefined}>
          <div className="avatar">{initial}</div>
          {!collapsed && (
            <div className="user-info">
              <div className="uname">{session.name}</div>
              <div className="urole">{session.role}</div>
            </div>
          )}
        </div>
      )}
    </nav>
  );
}
