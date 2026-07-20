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
 *   size        "sm" | "md" | "lg"
 *   className   string
 */
export function EmptyState({
  icon,
  title,
  description,
  action,
  dashed = true,
  size = "md",
  className = "",
}) {
  const padding = { sm: "32px 24px", md: "52px 32px", lg: "80px 48px" }[size] || "52px 32px";
  const iconSize = { sm: 20, md: 28, lg: 36 }[size] || 28;
  const titleSize = { sm: "0.82rem", md: "0.9rem", lg: "1rem" }[size] || "0.9rem";

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
            style: { color: TEXT_MUTED, ...(icon.props.style || {}) },
          })}
        </div>
      )}
      <p
        style={{
          fontSize: titleSize,
          fontWeight: 600,
          color: TEXT_STRONG,
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
            color: TEXT_MUTED,
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
