/* eslint-disable */
import React from "react";
import { TEXT_PRIMARY, TEXT_MUTED, BRD, SPACE } from "@/lib/tokens";

/**
 * Section — consistent content section with optional heading + action.
 *
 * Props:
 *   title     string       section heading
 *   subtitle  string       section sub-heading
 *   action    ReactNode    right-side element (button, link)
 *   gap       "sm"|"md"|"lg"  spacing between children (default: "md")
 *   divided   boolean      add a top border (default: false)
 *   children  ReactNode
 */
export function Section({
  title,
  subtitle,
  action,
  gap = "md",
  divided = false,
  style,
  className,
  children,
  ...props
}) {
  const GAP = { sm: SPACE.xs, md: SPACE.md, lg: SPACE.lg };

  return (
    <section
      style={{
        borderTop: divided ? `1px solid ${BRD}` : undefined,
        paddingTop: divided ? SPACE.lg : undefined,
        ...style,
      }}
      className={className}
      {...props}
    >
      {(title || action) && (
        <div style={{
          display: "flex",
          alignItems: subtitle ? "flex-start" : "center",
          justifyContent: "space-between",
          gap: SPACE.xs,
          marginBottom: SPACE.md,
        }}>
          <div style={{ minWidth: 0 }}>
            {title && (
              <h2 style={{
                margin: 0,
                fontSize: 14,
                fontWeight: 700,
                color: TEXT_PRIMARY,
                letterSpacing: "-0.015em",
                lineHeight: 1.3,
              }}>
                {title}
              </h2>
            )}
            {subtitle && (
              <p style={{ margin: "3px 0 0", fontSize: 12, color: TEXT_MUTED, lineHeight: 1.4 }}>
                {subtitle}
              </p>
            )}
          </div>
          {action && <div style={{ flexShrink: 0 }}>{action}</div>}
        </div>
      )}

      <div style={{ display: "flex", flexDirection: "column", gap: GAP[gap] ?? SPACE.md }}>
        {children}
      </div>
    </section>
  );
}

export default Section;
