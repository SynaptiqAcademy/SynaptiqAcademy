import React from "react";
import { Link } from "react-router-dom";
import {
  NAVY, BRD, BRDH, WARM, WHITE, SURF2, EMERALD, CRIMSON,
  TEXT_MUTED, TEXT_TERTIARY, FONT_SERIF, RADIUS_MD, RADIUS_FULL,
  SHADOW_CARD, SHADOW_CARD_HOVER, SUCCESS_BG, DANGER_BG,
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

  return (
    <Tag
      to={to}
      className={className}
      onClick={onClick}
      onMouseEnter={isInteractive ? () => setHovered(true) : undefined}
      onMouseLeave={isInteractive ? () => setHovered(false) : undefined}
      style={{
        textDecoration: "none",
        background: WHITE,
        border: `1px solid ${highlight ? NAVY : hovered && isInteractive ? BRDH : BRD}`,
        borderRadius: RADIUS_MD,
        padding: "18px 20px",
        display: "flex",
        flexDirection: "column",
        gap: 6,
        cursor: isInteractive ? "pointer" : "default",
        transition: "border-color 150ms, box-shadow 150ms",
        boxShadow: hovered && isInteractive ? SHADOW_CARD_HOVER : SHADOW_CARD,
      }}
    >
      {/* Top row: label + icon */}
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
        {label && (
          <p
            style={{
              fontSize: "0.62rem",
              fontWeight: 700,
              letterSpacing: "0.12em",
              textTransform: "uppercase",
              color: TEXT_MUTED,
              margin: 0,
            }}
          >
            {label}
          </p>
        )}
        {icon && (
          <div
            style={{
              width: 28,
              height: 28,
              borderRadius: RADIUS_MD,
              background: highlight ? NAVY : WARM,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
            }}
          >
            {React.cloneElement(icon, {
              size: 13,
              style: { color: highlight ? WHITE : TEXT_TERTIARY, ...(icon.props.style || {}) },
            })}
          </div>
        )}
      </div>

      {/* Value */}
      <p
        style={{
          fontFamily: FONT_SERIF,
          fontSize: "clamp(1.4rem, 3vw, 1.8rem)",
          fontWeight: 700,
          color: NAVY,
          letterSpacing: "-0.03em",
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
