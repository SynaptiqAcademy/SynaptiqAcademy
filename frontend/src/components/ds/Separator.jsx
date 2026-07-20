import React from "react";
import { BRD, BRDX, TEXT_MUTED, TYPE } from "@/lib/tokens";

/**
 * Separator — section divider system.
 *
 * Variants:
 *   line      — thin horizontal rule (default)
 *   labeled   — rule with a centered or left-aligned label
 *   spacer    — invisible height spacer (no line)
 *
 * Usage:
 *   <Separator />
 *   <Separator variant="labeled" label="Active Projects" />
 *   <Separator variant="spacer" size="lg" />
 */
export function Separator({
  variant = "line",
  label,
  align = "left",
  size = "md",
  style,
  ...props
}) {
  const margin = { sm: "12px 0", md: "20px 0", lg: "32px 0" }[size] || "20px 0";

  if (variant === "spacer") {
    const height = { sm: 12, md: 20, lg: 32 }[size] || 20;
    return <div style={{ height, flexShrink: 0, ...style }} aria-hidden="true" {...props} />;
  }

  if (variant === "labeled" && label) {
    const isCenter = align === "center";
    return (
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: 10,
          margin,
          ...style,
        }}
        role="separator"
        aria-label={label}
        {...props}
      >
        {!isCenter && <div style={{ flex: 1, height: 1, background: BRDX }} />}
        {isCenter && <div style={{ flex: 1, height: 1, background: BRDX }} />}
        <span
          style={{
            ...TYPE.label,
            color: TEXT_MUTED,
            whiteSpace: "nowrap",
            flexShrink: 0,
          }}
        >
          {label}
        </span>
        <div style={{ flex: 1, height: 1, background: BRDX }} />
      </div>
    );
  }

  return (
    <div
      style={{
        height: 1,
        background: BRDX,
        margin,
        ...style,
      }}
      role="separator"
      aria-hidden="true"
      {...props}
    />
  );
}

/**
 * SectionDivider — heavier separator between major page sections.
 * Used to visually separate top-level content areas.
 */
export function SectionDivider({ style, ...props }) {
  return (
    <div
      style={{
        height: 1,
        background: BRD,
        margin: "28px 0",
        ...style,
      }}
      role="separator"
      aria-hidden="true"
      {...props}
    />
  );
}

export default Separator;
