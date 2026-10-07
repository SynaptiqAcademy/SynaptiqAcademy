import React from "react";
import { NAVY, BRD, WHITE, TEXT_MUTED, TEXT_PRIMARY, TEXT_TERTIARY } from "@/lib/tokens";

/**
 * EmptyState — unified empty / zero-data state.
 *
 * Props:
 *   icon        ReactNode         — Lucide icon element
 *   title       string            — Primary message (required)
 *   description string            — Supporting description
 *   action      ReactNode         — CTA button / link
 *   dashed      bool              — Show dashed border container (default: true)
 *   size        "inline" | "sm" | "md" | "lg"
 *   dark        bool              — For placement on a dark/navy surface (e.g.
 *                                   a dark sidebar) rather than the app's
 *                                   light background — icon renders without
 *                                   its box wrapper and both icon/title use
 *                                   translucent white instead of the
 *                                   light-surface text tokens. `dashed`/
 *                                   `SURF2` container styling is skipped
 *                                   entirely in this mode (a dashed light
 *                                   border reads wrong on a dark fill).
 *   className   string
 *
 * size="inline" — a single muted caption line (no icon box, no padding, no
 * border regardless of `dashed`) for embedding inside an already-padded
 * panel/list rather than presenting as its own zero-data block — replaces
 * the hand-rolled `<p style={{fontStyle:"italic",color:muted}}>No X yet</p>`
 * pattern duplicated across several pages (e.g. AIAssistant.jsx, AIUsage.jsx).
 */
export function EmptyState({
  icon,
  title,
  description,
  action,
  dashed = true,
  size = "md",
  dark = false,
  className = "",
}) {
  if (size === "inline") {
    return (
      <p className={className} style={{ fontSize: "0.8rem", color: TEXT_MUTED, margin: 0 }}>
        {title}
      </p>
    );
  }

  // Compact and left-aligned: what is empty, why it matters, what to do
  // next. A light hairline panel, never a large dashed placeholder box.
  const padding = { sm: "14px 16px", md: "18px 20px", lg: "24px 24px" }[size] || "18px 20px";
  const iconSize = { sm: 14, md: 16, lg: 18 }[size] || 16;
  const titleSize = { sm: "0.84rem", md: "0.9rem", lg: "0.95rem" }[size] || "0.9rem";

  if (dark) {
    return (
      <div className={className} style={{ padding, textAlign: "center" }}>
        {icon && React.cloneElement(icon, { size: iconSize + 4, style: { color: "rgba(255,255,255,0.3)", marginBottom: 8, ...(icon.props.style || {}) } })}
        <div style={{ fontSize: titleSize, color: "rgba(255,255,255,0.45)" }}>{title}</div>
        {description && <p style={{ fontSize: "0.78rem", color: "rgba(255,255,255,0.35)", marginTop: 4 }}>{description}</p>}
        {action && <div style={{ marginTop: 12 }}>{action}</div>}
      </div>
    );
  }

  return (
    <div
      className={className}
      style={{
        padding: dashed ? padding : "4px 0",
        background: dashed ? WHITE : "transparent",
        border: dashed ? `1px solid ${BRD}` : "none",
        borderRadius: 6,
      }}
    >
      <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
        {icon && React.cloneElement(icon, {
          size: iconSize,
          strokeWidth: 1.75,
          "aria-hidden": true,
          style: { color: NAVY, flexShrink: 0, ...(icon.props.style || {}) },
        })}
        <div style={{ fontSize: titleSize, fontWeight: 600, color: TEXT_PRIMARY, letterSpacing: "-0.005em" }}>
          {title}
        </div>
      </div>
      {description && (
        <p style={{ fontSize: "0.8125rem", color: TEXT_TERTIARY, margin: "4px 0 0", lineHeight: 1.55, maxWidth: "34rem" }}>
          {description}
        </p>
      )}
      {action && <div style={{ marginTop: 12, display: "flex", flexWrap: "wrap", gap: 8 }}>{action}</div>}
    </div>
  );
}

export default EmptyState;
