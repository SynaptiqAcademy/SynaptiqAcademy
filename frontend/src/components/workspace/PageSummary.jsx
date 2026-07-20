import React from "react";
import {
  NAVY,
  BRD,
  WHITE,
  SHADOW_CARD,
  RADIUS_BASE,
  TEXT_PRIMARY,
  TEXT_SECONDARY,
  TEXT_MUTED,
  EMERALD,
} from "@/lib/tokens";

/**
 * PageSummary — the single premium contextual card directly below PageHeader.
 *
 * Every page gets one. It shows the most important context for the current view:
 * key stats, an active focus item, a deadline notice, or a smart insight.
 *
 * Props:
 *   title       string             — section label (small caps, muted)
 *   description string|ReactNode  — primary message (bold)
 *   stats       StatItem[]         — horizontal stat pills
 *   accent      string             — left-border color (defaults to NAVY)
 *   actions     ReactNode          — right-side action buttons
 *   children    ReactNode          — custom content below the stats row
 *
 * StatItem: { label, value, change?, trend?: "up"|"down"|"flat", color? }
 */
export function PageSummary({
  title,
  description,
  stats = [],
  accent,
  actions,
  children,
}) {
  const accentColor = accent || NAVY;
  const hasHeader = title || description || actions;
  const hasStats = stats.length > 0;

  return (
    <div
      style={{
        background: WHITE,
        border: `1px solid ${BRD}`,
        borderLeft: `3px solid ${accentColor}`,
        borderRadius: RADIUS_BASE,
        boxShadow: SHADOW_CARD,
        overflow: "hidden",
      }}
    >
      {/* Header zone */}
      {hasHeader && (
        <div
          style={{
            display: "flex",
            alignItems: "flex-start",
            justifyContent: "space-between",
            gap: 16,
            padding: "12px 18px",
            borderBottom: (hasStats || children) ? `1px solid ${BRD}` : "none",
          }}
        >
          <div style={{ minWidth: 0 }}>
            {title && (
              <p
                style={{
                  fontSize: "0.68rem",
                  fontWeight: 700,
                  letterSpacing: "0.08em",
                  textTransform: "uppercase",
                  color: TEXT_MUTED,
                  margin: 0,
                }}
              >
                {title}
              </p>
            )}
            {description && (
              <p
                style={{
                  fontSize: "0.85rem",
                  fontWeight: 500,
                  color: TEXT_PRIMARY,
                  margin: title ? "3px 0 0" : "0",
                  lineHeight: 1.45,
                }}
              >
                {description}
              </p>
            )}
          </div>

          {actions && (
            <div style={{ display: "flex", alignItems: "center", gap: 8, flexShrink: 0 }}>
              {actions}
            </div>
          )}
        </div>
      )}

      {/* Stats row */}
      {hasStats && (
        <div
          style={{
            display: "flex",
            padding: "10px 18px",
            flexWrap: "wrap",
            gap: 0,
          }}
        >
          {stats.map((stat, i) => (
            <StatPill
              key={i}
              {...stat}
              isLast={i === stats.length - 1}
            />
          ))}
        </div>
      )}

      {/* Custom content */}
      {children && (
        <div style={{ padding: hasHeader || hasStats ? "0 18px 12px" : "12px 18px" }}>
          {children}
        </div>
      )}
    </div>
  );
}

function StatPill({ label, value, change, trend, color, isLast }) {
  const trendColor =
    trend === "up"   ? EMERALD :
    trend === "down" ? "#DC2626" :
    TEXT_MUTED;

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        gap: 1,
        paddingRight: isLast ? 0 : 20,
        marginRight: isLast ? 0 : 20,
        borderRight: isLast ? "none" : `1px solid ${BRD}`,
        minWidth: 72,
      }}
    >
      <div style={{ display: "flex", alignItems: "baseline", gap: 5 }}>
        <span
          style={{
            fontSize: "1.05rem",
            fontWeight: 700,
            color: color || TEXT_PRIMARY,
            letterSpacing: "-0.02em",
            lineHeight: 1.2,
            fontVariantNumeric: "tabular-nums",
          }}
        >
          {value}
        </span>
        {change && (
          <span
            style={{
              fontSize: "0.7rem",
              fontWeight: 600,
              color: trendColor,
              letterSpacing: "0.01em",
            }}
          >
            {change}
          </span>
        )}
      </div>
      <span
        style={{
          fontSize: "0.68rem",
          color: TEXT_MUTED,
          letterSpacing: "0.01em",
          lineHeight: 1.3,
        }}
      >
        {label}
      </span>
    </div>
  );
}

export { StatPill };
export default PageSummary;
