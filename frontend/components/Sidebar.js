import React from "react";
import Logo from "./Logo";
import {
  IconOverview,
  IconForecast,
  IconFraud,
  IconChat,
  IconAgent,
  IconSignOut,
  IconSidebarToggle,
} from "./icons";

const NAV_ITEMS = [
  { id: "overview", label: "Overview", Icon: IconOverview },
  { id: "forecast", label: "Product forecast", Icon: IconForecast },
  { id: "fraud", label: "Fraud alerts", Icon: IconFraud },
  { id: "chat", label: "Document Q&A", Icon: IconChat },
  { id: "agent", label: "Agent activity", Icon: IconAgent },
];

export default function Sidebar({
  tab,
  setTab,
  session,
  onLogout,
  collapsed,
  setCollapsed,
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
        {NAV_ITEMS.map(({ id, label, Icon }) => {
          const isActive = tab === id;
          return (
            <button
              key={id}
              type="button"
              className={`navitem ${isActive ? "active" : ""}`}
              onClick={() => setTab(id)}
              aria-label={label}
              title={collapsed ? label : undefined}
            >
              <span className="navicon">
                <Icon size={20} />
              </span>
              {!collapsed && <span className="navlabel">{label}</span>}
              {collapsed && <span className="sidebar-tooltip">{label}</span>}
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
