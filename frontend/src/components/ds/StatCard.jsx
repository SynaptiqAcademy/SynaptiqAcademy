import React from "react";
import { Link } from "react-router-dom";
import {
  NAVY, BRD, BRDH, WHITE, SURF2, EMERALD, CRIMSON,
  TEXT_PRIMARY, TEXT_MUTED, TEXT_TERTIARY, FONT_SERIF, RADIUS_FULL,
  SUCCESS_BG, DANGER_BG,
} from "@/lib/tokens";

/**
 * StatCard — the one numeric-metric display card in the design system
 * (also covers what used to be a separate "MetricCard").
 *
 * Props:
 *   label        string          — Metric label (overline style)
 *   value        string|number   — The big number / value
 *   sub          string|node     — Sub-line below the value
 *   icon         ReactNode       — Lucide icon
 *   trend        number          — Trend % (positive = green, negative = red)
 *   highlight    bool            — Navy border accent (primary metric)
 *   onClick      function        — Makes card interactive
 *   to           string          — Renders as a Link, makes card interactive
 *   className    string
 */
const isEmptyValue = (v) => {
  if (v === null || v === undefined) return true;
  const t = String(typeof v === "object" ? "x" : v).trim();
  return ["", "0", "—", "-", "0%", "+0%", "+0", "0.0", "0/0", "0h", "$0.00", "€0"].includes(t);
};

export function StatCard({
  label,
  value,
  sub,
  icon,
  trend,
  highlight = false,
  onClick,
  to,
  className = "",
}) {
  const isInteractive = !!(onClick || to);
  const [hovered, setHovered] = React.useState(false);

  const trendColor =
    trend == null ? null : trend > 0 ? EMERALD : trend < 0 ? CRIMSON : TEXT_TERTIARY;
  const trendSign = trend > 0 ? "+" : "";

  const Tag = to ? Link : "div";
  // Marked so a container of only-empty metrics can be hidden in CSS
  // (index.css: .sq-stat / .is-empty), whatever wraps the cards.
  const empty = isEmptyValue(value);

  return (
    <Tag
      to={to}
      className={`sq-stat ${empty ? "is-empty" : ""} ${className}`}
      onClick={onClick}
      onMouseEnter={isInteractive ? () => setHovered(true) : undefined}
      onMouseLeave={isInteractive ? () => setHovered(false) : undefined}
      style={{
        textDecoration: "none",
        background: WHITE,
        border: `1px solid ${hovered && isInteractive ? BRDH : BRD}`,
        borderTop: highlight ? `2px solid ${NAVY}` : undefined,
        borderRadius: 6,
        padding: "14px 16px",
        display: "flex",
        flexDirection: "column",
        gap: 4,
        cursor: isInteractive ? "pointer" : "default",
        transition: "border-color 150ms",
      }}
    >
      {/* Top row: label + icon */}
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
        {label && (
          <p
            style={{
              fontSize: "0.75rem",
              fontWeight: 500,
              color: TEXT_TERTIARY,
              margin: 0,
            }}
          >
            {label}
          </p>
        )}
        {icon && React.cloneElement(icon, {
          size: 14,
          strokeWidth: 1.6,
          "aria-hidden": true,
          style: { color: TEXT_MUTED, ...(icon.props.style || {}) },
        })}
      </div>

      {/* Value */}
      <p
        style={{
          fontFamily: FONT_SERIF,
          fontSize: "1.6rem",
          fontWeight: 400,
          color: TEXT_PRIMARY,
          letterSpacing: "-0.01em",
          fontVariantNumeric: "tabular-nums",
          lineHeight: 1,
          margin: 0,
        }}
      >
        {value ?? "—"}
      </p>

      {/* Sub-line + trend */}
      {(sub || trend != null) && (
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          {sub && (
            <p style={{ fontSize: "0.72rem", color: TEXT_TERTIARY, margin: 0, flex: 1 }}>{sub}</p>
          )}
          {trend != null && (
            <span
              style={{
                fontSize: "0.68rem",
                fontWeight: 600,
                color: trendColor,
                background: trend > 0 ? SUCCESS_BG : trend < 0 ? DANGER_BG : SURF2,
                padding: "1px 6px",
                borderRadius: RADIUS_FULL,
                flexShrink: 0,
              }}
            >
              {trendSign}{trend}%
            </span>
          )}
        </div>
      )}
    </Tag>
  );
}

/**
 * StatGrid — responsive grid of StatCards.
 * cols: number of columns at large screen (default: 4)
 */


export function StatGrid({ children, cols = 4, className = "" }) {
  // A grid of zeros earns no space: when every metric is empty the grid is
  // left out, and appears as soon as there is something to report.
  const flat = (kids) => React.Children.toArray(kids).flatMap((c) => (c && c.type === React.Fragment ? flat(c.props.children) : [c]));
  const items = flat(children).filter(Boolean);
  const valued = items.filter((c) => c && c.props && "value" in c.props);
  if (valued.length > 0 && valued.length === items.length && valued.every((c) => isEmptyValue(c.props.value))) return null;
  return (
    <div
      className={className}
      style={{
        display: "grid",
        gridTemplateColumns: `repeat(auto-fill, minmax(${Math.floor(800 / cols)}px, 1fr))`,
        gap: 12,
      }}
    >
      {children}
    </div>
  );
}

export default StatCard;
