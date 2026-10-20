import React from "react";

const baseProps = (size = 20) => ({
  width: size,
  height: size,
  viewBox: "0 0 24 24",
  fill: "none",
  stroke: "currentColor",
  strokeWidth: 1.75,
  strokeLinecap: "round",
  strokeLinejoin: "round",
  style: { flexShrink: 0 },
});

// Overview: dashboard grid (four rounded squares)
export function IconOverview({ size = 20, ...props }) {
  return (
    <svg {...baseProps(size)} {...props}>
      <rect x="3" y="3" width="7" height="7" rx="1.5" />
      <rect x="14" y="3" width="7" height="7" rx="1.5" />
      <rect x="3" y="14" width="7" height="7" rx="1.5" />
      <rect x="14" y="14" width="7" height="7" rx="1.5" />
    </svg>
  );
}

// Product forecast: rising line chart with an arrow (trending up)
export function IconForecast({ size = 20, ...props }) {
  return (
    <svg {...baseProps(size)} {...props}>
      <polyline points="22 7 13.5 15.5 8.5 10.5 2 17" />
      <polyline points="16 7 22 7 22 13" />
    </svg>
  );
}

// Fraud alerts: shield with an exclamation mark
export function IconFraud({ size = 20, ...props }) {
  return (
    <svg {...baseProps(size)} {...props}>
      <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
      <line x1="12" y1="8" x2="12" y2="12" />
      <line x1="12" y1="16" x2="12.01" y2="16" strokeWidth="2.5" />
    </svg>
  );
}

// Document Q&A: document with a chat bubble or magnifier
export function IconChat({ size = 20, ...props }) {
  return (
    <svg {...baseProps(size)} {...props}>
      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
      <polyline points="14 2 14 8 20 8" />
      <path d="M9 13h6" />
      <path d="M9 17h4" />
    </svg>
  );
}

// Agent activity: friendly robot head with antenna
export function IconAgent({ size = 20, ...props }) {
  return (
    <svg {...baseProps(size)} {...props}>
      <rect x="4" y="8" width="16" height="12" rx="3" />
      <line x1="12" y1="4" x2="12" y2="8" />
      <circle cx="12" cy="3" r="1" fill="currentColor" />
      <line x1="2" y1="14" x2="4" y2="14" />
      <line x1="20" y1="14" x2="22" y2="14" />
      <circle cx="9" cy="13" r="1.25" fill="currentColor" />
      <circle cx="15" cy="13" r="1.25" fill="currentColor" />
      <path d="M9 17h6" />
    </svg>
  );
}

// Sign out: arrow leaving a door
export function IconSignOut({ size = 20, ...props }) {
  return (
    <svg {...baseProps(size)} {...props}>
      <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" />
      <polyline points="16 17 21 12 16 7" />
      <line x1="21" y1="12" x2="9" y2="12" />
    </svg>
  );
}

// Sidebar toggle: panel with chevron
export function IconSidebarToggle({ size = 18, collapsed = false, ...props }) {
  return (
    <svg {...baseProps(size)} {...props}>
      <rect x="3" y="3" width="18" height="18" rx="2" />
      <line x1="9" y1="3" x2="9" y2="21" />
      {collapsed ? (
        <polyline points="13 9 16 12 13 15" />
      ) : (
        <polyline points="16 9 13 12 16 15" />
      )}
    </svg>
  );
}

// Upload zone: upload cloud/tray
export function IconUpload({ size = 20, ...props }) {
  return (
    <svg {...baseProps(size)} {...props}>
      <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
      <polyline points="17 8 12 3 7 8" />
      <line x1="12" y1="3" x2="12" y2="15" />
    </svg>
  );
}

// Trash: clear history
export function IconTrash({ size = 18, ...props }) {
  return (
    <svg {...baseProps(size)} {...props}>
      <polyline points="3 6 5 6 21 6" />
      <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
      <line x1="10" y1="11" x2="10" y2="17" />
      <line x1="14" y1="11" x2="14" y2="17" />
    </svg>
  );
}

// Calendar: date dropdown
export function IconCalendar({ size = 18, ...props }) {
  return (
    <svg {...baseProps(size)} {...props}>
      <rect x="3" y="4" width="18" height="18" rx="2" />
      <line x1="16" y1="2" x2="16" y2="6" />
      <line x1="8" y1="2" x2="8" y2="6" />
      <line x1="3" y1="10" x2="21" y2="10" />
    </svg>
  );
}

// Download: template CSV
export function IconDownload({ size = 16, ...props }) {
  return (
    <svg {...baseProps(size)} {...props}>
      <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
      <polyline points="7 10 12 15 17 10" />
      <line x1="12" y1="15" x2="12" y2="3" />
    </svg>
  );
}

// Chevrons
export function IconChevronDown({ size = 18, ...props }) {
  return (
    <svg {...baseProps(size)} {...props}>
      <polyline points="6 9 12 15 18 9" />
    </svg>
  );
}

export function IconChevronUp({ size = 18, ...props }) {
  return (
    <svg {...baseProps(size)} {...props}>
      <polyline points="18 15 12 9 6 15" />
    </svg>
  );
}

export function IconChevronRight({ size = 18, ...props }) {
  return (
    <svg {...baseProps(size)} {...props}>
      <polyline points="9 18 15 12 9 6" />
    </svg>
  );
}

// Bell: notifications
export function IconBell({ size = 20, ...props }) {
  return (
    <svg {...baseProps(size)} {...props}>
      <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9" />
      <path d="M13.73 21a2 2 0 0 1-3.46 0" />
    </svg>
  );
}

// File / Report: reports
export function IconReport({ size = 20, ...props }) {
  return (
    <svg {...baseProps(size)} {...props}>
      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
      <polyline points="14 2 14 8 20 8" />
      <line x1="16" y1="13" x2="8" y2="13" />
      <line x1="16" y1="17" x2="8" y2="17" />
      <polyline points="10 9 9 9 8 9" />
    </svg>
  );
}

// Clock: overdue / reminders
export function IconClock({ size = 18, ...props }) {
  return (
    <svg {...baseProps(size)} {...props}>
      <circle cx="12" cy="12" r="10" />
      <polyline points="12 6 12 12 16 14" />
    </svg>
  );
}

// Mail: report sent / email
export function IconMail({ size = 18, ...props }) {
  return (
    <svg {...baseProps(size)} {...props}>
      <path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z" />
      <polyline points="22,6 12,13 2,6" />
    </svg>
  );
}

// Gear: settings
export function IconGear({ size = 18, ...props }) {
  return (
    <svg {...baseProps(size)} {...props}>
      <circle cx="12" cy="12" r="3" />
      <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z" />
    </svg>
  );
}

// Users: repeat offender
export function IconUsers({ size = 18, ...props }) {
  return (
    <svg {...baseProps(size)} {...props}>
      <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" />
      <circle cx="9" cy="7" r="4" />
      <path d="M23 21v-2a4 4 0 0 0-3-3.87" />
      <path d="M16 3.13a4 4 0 0 1 0 7.75" />
    </svg>
  );
}

// Trending down: forecast drop
export function IconTrendingDown({ size = 18, ...props }) {
  return (
    <svg {...baseProps(size)} {...props}>
      <polyline points="23 18 13.5 8.5 8.5 13.5 1 6" />
      <polyline points="17 18 23 18 23 12" />
    </svg>
  );
}

// Info: info notification
export function IconInfo({ size = 18, ...props }) {
  return (
    <svg {...baseProps(size)} {...props}>
      <circle cx="12" cy="12" r="10" />
      <line x1="12" y1="16" x2="12" y2="12" />
      <line x1="12" y1="8" x2="12.01" y2="8" strokeWidth="2.5" />
    </svg>
  );
}

// Check: success / mark read
export function IconCheck({ size = 18, ...props }) {
  return (
    <svg {...baseProps(size)} {...props}>
      <polyline points="20 6 9 17 4 12" />
    </svg>
  );
}

// X: reject / cancel / close
export function IconX({ size = 18, ...props }) {
  return (
    <svg {...baseProps(size)} {...props}>
      <line x1="18" y1="6" x2="6" y2="18" />
      <line x1="6" y1="6" x2="18" y2="18" />
    </svg>
  );
}

// Refresh: reload / checks
export function IconRefresh({ size = 18, ...props }) {
  return (
    <svg {...baseProps(size)} {...props}>
      <polyline points="23 4 23 10 17 10" />
      <polyline points="1 20 1 14 7 14" />
      <path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15" />
    </svg>
  );
}
