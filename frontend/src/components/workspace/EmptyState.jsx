import React from "react";
import { NAVY, BRD, RADIUS_BASE, TEXT_MUTED } from "@/lib/tokens";

/**
 * EmptyState — consistent zero-data state for workspace pages.
 *
 * Props:
 *   icon         ReactNode          — Lucide icon element
 *   title        string             — primary message (required)
 *   description  string|ReactNode   — supporting description
 *   action       ReactNode          — CTA button or link
 *   size         "sm" | "md" | "lg"
 *   dashed       bool               — show dashed border container (default: true)
 */
export function EmptyState({
  icon,
  title,
  description,
  action,
  size = "md",
  dashed = true,
}) {
  const PAD   = { sm: "28px 20px", md: "48px 28px", lg: "72px 40px" }[size] || "48px 28px";
  const ISIZE = { sm: 18, md: 26, lg: 34 }[size] || 26;
  const TSIZE = { sm: "0.78rem", md: "0.87rem", lg: "0.95rem" }[size] || "0.87rem";

  const inner = (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        textAlign: "center",
        padding: PAD,
      }}
    >
      {icon && (
        <div
          style={{
            width: ISIZE + 20,
            height: ISIZE + 20,
            borderRadius: 8,
            background: "rgba(15,40,71,0.05)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            marginBottom: 14,
          }}
        >
          {React.isValidElement(icon)
            ? React.cloneElement(icon, {
                size: ISIZE,
                style: { color: "#94a3b8", ...(icon.props.style || {}) },
              })
            : icon}
        </div>
      )}

      <p
        style={{
          fontSize: TSIZE,
          fontWeight: 600,
          color: "#374151",
          margin: 0,
          letterSpacing: "-0.01em",
        }}
      >
        {title}
      </p>

      {description && (
        <p
          style={{
            fontSize: "0.75rem",
            color: TEXT_MUTED,
            marginTop: 6,
            lineHeight: 1.55,
            maxWidth: 320,
          }}
        >
          {description}
        </p>
      )}

      {action && <div style={{ marginTop: 18 }}>{action}</div>}
    </div>
  );

  if (dashed) {
    return (
      <div
        style={{
          border: "1px dashed #CBD5E1",
          borderRadius: RADIUS_BASE,
          background: "#FAFBFC",
        }}
      >
        {inner}
      </div>
    );
  }

  return inner;
}

export default EmptyState;
