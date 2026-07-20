/* eslint-disable */
import React from "react";
import { Link } from "react-router-dom";
import { BRD, TEXT_PRIMARY, TEXT_MUTED, WARM, WHITE, NAVY_06, RADIUS_LG } from "@/lib/tokens";

// ── List ──────────────────────────────────────────────────────────────────────
// Wraps ListItems with optional border and radius.

export function List({ border = true, radius = RADIUS_LG, divided = true, style, children, ...props }) {
  return (
    <div style={{
      background: WHITE,
      border: border ? `1px solid ${BRD}` : "none",
      borderRadius: radius,
      overflow: "hidden",
      ...style,
    }} {...props}>
      {children}
    </div>
  );
}

// ── ListItem ──────────────────────────────────────────────────────────────────

export function ListItem({
  title,
  subtitle,
  leading,
  trailing,
  to,
  href,
  onClick,
  selected = false,
  compact = false,
  disabled = false,
  style,
  children,
  ...props
}) {
  const [hov, setHov] = React.useState(false);
  const interactive = !!(to || href || onClick) && !disabled;

  const base = {
    display: "flex",
    alignItems: "center",
    gap: 12,
    padding: compact ? "8px 16px" : "12px 16px",
    borderBottom: `1px solid ${BRD}`,
    background: selected ? NAVY_06 : hov && interactive ? WARM : "transparent",
    cursor: interactive ? "pointer" : "default",
    transition: "background 100ms",
    opacity: disabled ? 0.45 : 1,
    textDecoration: "none",
    color: "inherit",
    ...style,
  };

  const handlers = {
    onMouseEnter: () => setHov(true),
    onMouseLeave: () => setHov(false),
  };

  const inner = (
    <>
      {leading && <div style={{ flexShrink: 0 }}>{leading}</div>}
      <div style={{ flex: 1, minWidth: 0 }}>
        {title && (
          <p style={{ margin: 0, fontSize: "0.875rem", fontWeight: 500, color: TEXT_PRIMARY, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
            {title}
          </p>
        )}
        {subtitle && (
          <p style={{ margin: "1px 0 0", fontSize: "0.75rem", color: TEXT_MUTED, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
            {subtitle}
          </p>
        )}
        {!title && children}
      </div>
      {trailing && <div style={{ flexShrink: 0 }}>{trailing}</div>}
    </>
  );

  if (to) {
    return <Link to={to} style={base} {...handlers} {...props}>{inner}</Link>;
  }

  if (href) {
    return (
      <a href={href} style={base} target="_blank" rel="noopener noreferrer" {...handlers} {...props}>
        {inner}
      </a>
    );
  }

  return (
    <div
      role={interactive ? "button" : undefined}
      tabIndex={interactive ? 0 : undefined}
      onClick={!disabled ? onClick : undefined}
      onKeyDown={interactive
        ? (e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); onClick?.(e); } }
        : undefined}
      style={base}
      {...handlers}
      {...props}
    >
      {inner}
    </div>
  );
}

// ── ListSeparator ─────────────────────────────────────────────────────────────

export function ListSeparator({ label, style }) {
  return (
    <div style={{
      padding: label ? "6px 16px 4px" : "0",
      borderBottom: `1px solid ${BRD}`,
      background: WARM,
      ...style,
    }}>
      {label && (
        <span style={{
          fontSize: "0.625rem",
          fontWeight: 700,
          letterSpacing: "0.08em",
          textTransform: "uppercase",
          color: TEXT_MUTED,
        }}>
          {label}
        </span>
      )}
    </div>
  );
}

// ── ListFooter ────────────────────────────────────────────────────────────────

export function ListFooter({ children, style }) {
  return (
    <div style={{ padding: "8px 16px", borderTop: `1px solid ${BRD}`, background: WARM, ...style }}>
      {children}
    </div>
  );
}

// ── ListHeader ────────────────────────────────────────────────────────────────

export function ListHeader({ title, action, style }) {
  return (
    <div style={{
      display: "flex", alignItems: "center", justifyContent: "space-between",
      padding: "10px 16px", borderBottom: `1px solid ${BRD}`, background: WARM,
      ...style,
    }}>
      {title && (
        <span style={{ fontSize: "0.75rem", fontWeight: 700, letterSpacing: "0.04em", textTransform: "uppercase", color: TEXT_MUTED }}>
          {title}
        </span>
      )}
      {action && <div style={{ flexShrink: 0 }}>{action}</div>}
    </div>
  );
}
