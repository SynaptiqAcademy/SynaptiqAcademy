import React, { useState } from "react";
import { ChevronDown, ChevronRight } from "lucide-react";
import {
  BRD,
  TEXT_PRIMARY,
  TEXT_MUTED,
  RADIUS_PILL,
} from "@/lib/tokens";

/**
 * PageSection — content section with a consistent header row.
 *
 * Use inside PageContent (or directly as WorkspaceLayout children) to divide
 * content into labelled zones. Identical header styling on every page is what
 * makes the app feel like one product.
 *
 * Props:
 *   title        string     — section title (required)
 *   count        number     — optional item count badge
 *   action       ReactNode  — right-side action (link, button, or menu)
 *   description  string     — short subtitle shown inline after title
 *   collapsible  bool       — enable expand / collapse
 *   defaultOpen  bool       — initial expanded state (default: true)
 *   noBorder     bool       — remove the separator line above the header
 *   children     ReactNode  — section content
 */
export function PageSection({
  title,
  count,
  action,
  description,
  collapsible = false,
  defaultOpen = true,
  noBorder = false,
  children,
}) {
  const [open, setOpen] = useState(defaultOpen);
  const isOpen = collapsible ? open : true;

  return (
    <section>
      {/* ─── Section header ─── */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          paddingBottom: 10,
          marginBottom: isOpen ? 14 : 0,
          borderBottom: noBorder ? "none" : `1px solid ${BRD}`,
          cursor: collapsible ? "pointer" : "default",
          userSelect: collapsible ? "none" : "auto",
        }}
        onClick={collapsible ? () => setOpen((o) => !o) : undefined}
      >
        {/* Left: toggle icon + title + count + description */}
        <div style={{ display: "flex", alignItems: "center", gap: 7, minWidth: 0 }}>
          {collapsible && (
            <span style={{ color: TEXT_MUTED, flexShrink: 0, display: "flex" }}>
              {isOpen
                ? <ChevronDown size={12} strokeWidth={2.5} />
                : <ChevronRight size={12} strokeWidth={2.5} />
              }
            </span>
          )}

          <span
            style={{
              fontSize: "0.78rem",
              fontWeight: 600,
              color: TEXT_PRIMARY,
              letterSpacing: "-0.01em",
              lineHeight: 1.3,
            }}
          >
            {title}
          </span>

          {count != null && (
            <span
              style={{
                fontSize: "0.63rem",
                fontWeight: 700,
                color: "#64748b",
                background: "rgba(15,23,42,0.06)",
                borderRadius: RADIUS_PILL,
                padding: "1px 6px",
                letterSpacing: "0.02em",
                lineHeight: 1.6,
                fontVariantNumeric: "tabular-nums",
              }}
            >
              {count}
            </span>
          )}

          {description && (
            <span
              style={{
                fontSize: "0.72rem",
                color: TEXT_MUTED,
                marginLeft: 2,
              }}
            >
              {description}
            </span>
          )}
        </div>

        {/* Right: action (stopPropagation so collapse doesn't trigger) */}
        {action && (
          <div
            onClick={(e) => e.stopPropagation()}
            style={{ flexShrink: 0 }}
          >
            {action}
          </div>
        )}
      </div>

      {/* ─── Section body ─── */}
      {isOpen && children}
    </section>
  );
}

export default PageSection;
