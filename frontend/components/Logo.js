import React from "react";

export default function Logo({ collapsed = false, size = 34, style = {} }) {
  return (
    <div
      className="brand-logo-container"
      style={{
        display: "flex",
        alignItems: "center",
        gap: 10,
        textDecoration: "none",
        color: "inherit",
        ...style,
      }}
    >
      <svg
        width={size}
        height={size}
        viewBox="0 0 32 32"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        style={{ flexShrink: 0, borderRadius: 9 }}
      >
        <defs>
          <linearGradient id="fpLogoGrad" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="#3ECF8E" />
            <stop offset="100%" stopColor="#2A9D6F" />
          </linearGradient>
        </defs>
        <rect width="32" height="32" rx="8" fill="url(#fpLogoGrad)" />
        {/* Rising 3-point chart tail */}
        <polyline
          points="7,23.5 11.5,20.5 15.5,17.5"
          stroke="#08120D"
          strokeWidth="1.8"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
        <circle cx="7" cy="23.5" r="1.2" fill="#08120D" />
        <circle cx="11.5" cy="20.5" r="1.2" fill="#08120D" />
        {/* Paper plane / navigation arrow pointing up-right */}
        <polygon points="25,7 10,15.5 15.5,17.5 17.5,23" fill="#08120D" />
        <polygon points="25,7 15.5,17.5 17.5,23" fill="#050C09" opacity="0.25" />
      </svg>

      {!collapsed && (
        <span
          className="brand-name"
          style={{
            fontWeight: 700,
            fontSize: 17,
            letterSpacing: "-0.01em",
            whiteSpace: "nowrap",
            display: "flex",
            alignItems: "center",
            gap: 4,
          }}
        >
          <span>FinPilot</span>
          <span style={{ color: "var(--accent)" }}>AI</span>
        </span>
      )}
    </div>
  );
}
