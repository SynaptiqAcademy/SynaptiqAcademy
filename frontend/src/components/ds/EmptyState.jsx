import React from "react";
import { NAVY, BRD, NAVY_04, TEXT_MUTED, TEXT_STRONG, TEXT_DISABLED, SURF2, RADIUS_MD } from "@/lib/tokens";

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
      <p className={className} style={{ fontSize: "0.75rem", color: TEXT_MUTED, fontStyle: "italic", margin: 0 }}>
        {title}
      </p>
    );
  }

  const padding = { sm: "32px 24px", md: "52px 32px", lg: "80px 48px" }[size] || "52px 32px";
  const iconSize = { sm: 20, md: 28, lg: 36 }[size] || 28;
  const titleSize = { sm: "0.82rem", md: "0.9rem", lg: "1rem" }[size] || "0.9rem";

  const iconColor = dark ? "rgba(255,255,255,0.2)" : TEXT_MUTED;
  const titleColor = dark ? "rgba(255,255,255,0.3)" : TEXT_STRONG;
  const descColor = dark ? "rgba(255,255,255,0.25)" : TEXT_MUTED;

  const inner = (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        textAlign: "center",
        padding,
        gap: 0,
      }}
    >
      {icon && (
        dark ? (
          React.cloneElement(icon, {
            size: iconSize,
            style: { color: iconColor, marginBottom: 10, ...(icon.props.style || {}) },
          })
        ) : (
          <div
            style={{
              width: iconSize + 16,
              height: iconSize + 16,
              borderRadius: RADIUS_MD,
              background: NAVY_04,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              marginBottom: 16,
            }}
          >
            {React.cloneElement(icon, {
              size: iconSize,
              style: { color: iconColor, ...(icon.props.style || {}) },
            })}
          </div>
        )
      )}
      <p
        style={{
          fontSize: titleSize,
          fontWeight: dark ? 400 : 600,
          color: titleColor,
          margin: 0,
          letterSpacing: "-0.01em",
        }}
      >
        {title}
      </p>
      {description && (
        <p
          style={{
            fontSize: "0.78rem",
            color: descColor,
            marginTop: 6,
            lineHeight: 1.55,
            maxWidth: 340,
          }}
        >
          {description}
        </p>
      )}
      {action && <div style={{ marginTop: 20 }}>{action}</div>}
    </div>
  );

  if (dark) {
    return <div className={className}>{inner}</div>;
  }

  if (dashed) {
    return (
      <div
        className={className}
        style={{
          border: `1px dashed ${TEXT_DISABLED}`,
          borderRadius: RADIUS_MD,
          background: SURF2,
        }}
      >
        {inner}
      </div>
    );
  }

  return <div className={className}>{inner}</div>;
}

export default EmptyState;
