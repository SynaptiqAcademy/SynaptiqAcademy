import React from "react";
import {
  NAVY, BRD, NAVY_08, NAVY_12, WHITE, ADMIN_BG,
  TEXT_TERTIARY, TEXT_STRONG, RADIUS_MD, RADIUS_LG, RADIUS_FULL, ICON,
} from "@/lib/tokens";

/**
 * NavTabs — standardized horizontal tab bar.
 *
 * Variants:
 *   underline   — underline active tab (default, for page-level tabs)
 *   pill        — filled pill active tab (for sub-sections)
 *   segment     — full-width segmented control
 *
 * Props:
 *   tabs     [{ id, label, count?, icon?, disabled? }]
 *   active   string   — active tab id
 *   onChange function(id)
 *   variant  "underline" | "pill" | "segment"
 *   size     "sm" | "md"
 *   className string
 */
export function NavTabs({
  tabs = [],
  active,
  onChange,
  variant = "underline",
  size = "md",
  className = "",
}) {
  const isUnderline = variant === "underline";
  const isPill      = variant === "pill";
  const isSegment   = variant === "segment";

  const containerStyle = {
    underline: {
      display: "flex",
      gap: 0,
      borderBottom: `1px solid ${BRD}`,
    },
    pill: {
      display: "flex",
      gap: 4,
      flexWrap: "wrap",
    },
    segment: {
      display: "flex",
      background: ADMIN_BG,
      borderRadius: RADIUS_LG,
      padding: 3,
      gap: 2,
    },
  }[variant];

  return (
    <div className={className} style={containerStyle}>
      {tabs.map((tab) => {
        const isActive = tab.id === active;
        const isDisabled = tab.disabled;
        const Icon = tab.icon;

        let tabStyle = {};
        if (isUnderline) {
          tabStyle = {
            display: "inline-flex",
            alignItems: "center",
            gap: 6,
            padding: size === "sm" ? "8px 12px" : "10px 16px",
            fontSize: size === "sm" ? "0.76rem" : "0.8rem",
            fontWeight: isActive ? 700 : 400,
            color: isActive ? NAVY : TEXT_TERTIARY,
            borderBottom: isActive ? `2px solid ${NAVY}` : "2px solid transparent",
            background: "transparent",
            border: "none",
            cursor: isDisabled ? "not-allowed" : "pointer",
            opacity: isDisabled ? 0.4 : 1,
            whiteSpace: "nowrap",
            transition: "color 150ms",
            marginBottom: -1, // flush with border-bottom of container
            outline: "none",
          };
        } else if (isPill) {
          tabStyle = {
            display: "inline-flex",
            alignItems: "center",
            gap: 6,
            padding: size === "sm" ? "4px 10px" : "5px 14px",
            fontSize: size === "sm" ? "0.73rem" : "0.78rem",
            fontWeight: isActive ? 600 : 400,
            color: isActive ? NAVY : TEXT_TERTIARY,
            background: isActive ? NAVY_08 : "transparent",
            border: `1px solid ${isActive ? NAVY_12 : "transparent"}`,
            borderRadius: RADIUS_MD,
            cursor: isDisabled ? "not-allowed" : "pointer",
            opacity: isDisabled ? 0.4 : 1,
            whiteSpace: "nowrap",
            transition: "all 150ms",
            outline: "none",
          };
        } else if (isSegment) {
          tabStyle = {
            flex: 1,
            display: "inline-flex",
            alignItems: "center",
            justifyContent: "center",
            gap: 6,
            padding: size === "sm" ? "4px 10px" : "5px 12px",
            fontSize: size === "sm" ? "0.73rem" : "0.78rem",
            fontWeight: isActive ? 600 : 400,
            color: isActive ? NAVY : TEXT_TERTIARY,
            background: isActive ? WHITE : "transparent",
            boxShadow: isActive ? "0 1px 3px rgba(15,23,42,0.1)" : "none",
            border: "none",
            borderRadius: RADIUS_MD,
            cursor: isDisabled ? "not-allowed" : "pointer",
            opacity: isDisabled ? 0.4 : 1,
            whiteSpace: "nowrap",
            transition: "all 150ms",
            outline: "none",
          };
        }

        return (
          <button
            key={tab.id}
            onClick={() => !isDisabled && onChange?.(tab.id)}
            style={tabStyle}
            onMouseEnter={(e) => {
              if (!isActive && !isDisabled && isUnderline) e.currentTarget.style.color = TEXT_STRONG;
            }}
            onMouseLeave={(e) => {
              if (!isActive && !isDisabled && isUnderline) e.currentTarget.style.color = TEXT_TERTIARY;
            }}
          >
            {Icon && <Icon size={size === "sm" ? ICON.xs.size : ICON.sm.size} />}
            {tab.label}
            {tab.count != null && (
              <span
                style={{
                  fontSize: "0.62rem",
                  fontWeight: 700,
                  background: isActive ? NAVY : "#e2e8f0",
                  color: isActive ? WHITE : TEXT_TERTIARY,
                  borderRadius: RADIUS_FULL,
                  padding: "1px 5px",
                  lineHeight: "16px",
                }}
              >
                {tab.count}
              </span>
            )}
          </button>
        );
      })}
    </div>
  );
}

export default NavTabs;
