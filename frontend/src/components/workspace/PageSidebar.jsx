import React from "react";
import {
  BRD,
  WHITE,
  SHADOW_CARD,
  RADIUS_BASE,
  TEXT_MUTED,
} from "@/lib/tokens";

/**
 * PageSidebar — right context panel passed to WorkspaceLayout's sidebar prop.
 *
 * Usage:
 *   <WorkspaceLayout
 *     sidebar={
 *       <PageSidebar>
 *         <SidebarCard title="Deadlines" icon={<Calendar />}>…</SidebarCard>
 *         <SidebarCard title="Insights">…</SidebarCard>
 *         <AIAssistant context="manuscripts" />
 *       </PageSidebar>
 *     }
 *   >
 *
 * WorkspaceLayout makes the sidebar sticky at top: 76px automatically.
 */
export function PageSidebar({ children, gap = 12, style }) {
  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        gap,
        ...style,
      }}
    >
      {children}
    </div>
  );
}

/**
 * SidebarCard — a card widget inside the sidebar.
 *
 * Props:
 *   title    string     — card label (uppercase, muted)
 *   icon     ReactNode  — icon shown left of title
 *   actions  ReactNode  — right-side link/button
 *   noPad   bool       — remove body padding (for flush content like lists)
 *   children ReactNode  — card body
 */
export function SidebarCard({
  title,
  icon,
  actions,
  noPad = false,
  children,
}) {
  const hasHeader = title || icon || actions;

  return (
    <div
      style={{
        background: WHITE,
        border: `1px solid ${BRD}`,
        borderRadius: RADIUS_BASE,
        boxShadow: SHADOW_CARD,
        overflow: "hidden",
      }}
    >
      {hasHeader && (
        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            padding: "9px 14px",
            borderBottom: `1px solid ${BRD}`,
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
            {icon && React.isValidElement(icon) && (
              React.cloneElement(icon, {
                size: 12,
                style: { color: TEXT_MUTED, ...(icon.props.style || {}) },
              })
            )}
            {title && (
              <span
                style={{
                  fontSize: "0.68rem",
                  fontWeight: 700,
                  letterSpacing: "0.07em",
                  textTransform: "uppercase",
                  color: TEXT_MUTED,
                }}
              >
                {title}
              </span>
            )}
          </div>
          {actions && (
            <div style={{ fontSize: "0.72rem" }}>
              {actions}
            </div>
          )}
        </div>
      )}

      <div style={noPad ? {} : { padding: "12px 14px" }}>
        {children}
      </div>
    </div>
  );
}

/**
 * SidebarDivider — subtle visual break between sidebar sections.
 */
export function SidebarDivider({ label }) {
  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        gap: 8,
        padding: "2px 0",
      }}
    >
      {label && (
        <span
          style={{
            fontSize: "0.63rem",
            fontWeight: 700,
            letterSpacing: "0.08em",
            textTransform: "uppercase",
            color: TEXT_MUTED,
            whiteSpace: "nowrap",
          }}
        >
          {label}
        </span>
      )}
      <div style={{ flex: 1, height: 1, background: BRD }} />
    </div>
  );
}

export default PageSidebar;
