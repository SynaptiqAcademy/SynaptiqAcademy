import React from "react";
import { BRD, NAVY, NAVY_06, NAVY_20, SURF2, TEXT_SECONDARY, RADIUS_XS, RADIUS_SM } from "@/lib/tokens";

/**
 * Tag — user-applied or system-applied content label.
 *
 * Variants: default | active | removable | colored
 * Sizes:    sm | md (default) | lg
 */
export function Tag({
  children,
  variant = "default",
  size = "md",
  color,
  onRemove,
  onClick,
  className = "",
  style,
}) {
  const sizes = {
    sm: { height: 20, px: "6px", fontSize: "0.67rem", gap: 4, radius: RADIUS_XS },
    md: { height: 24, px: "8px", fontSize: "0.72rem", gap: 4, radius: RADIUS_SM },
    lg: { height: 28, px: "10px", fontSize: "0.78rem", gap: 6, radius: RADIUS_SM },
  }[size] || sizes?.md;

  const s = sizes || { height: 24, px: "8px", fontSize: "0.72rem", gap: 4, radius: 4 };

  const isActive = variant === "active";
  const isClickable = !!onClick;

  const baseStyle = {
    display: "inline-flex",
    alignItems: "center",
    gap: s.gap,
    height: s.height,
    padding: `0 ${s.px}`,
    fontSize: s.fontSize,
    fontWeight: isActive ? 500 : 400,
    borderRadius: s.radius,
    border: `1px solid ${isActive ? NAVY_20 : BRD}`,
    background: isActive ? NAVY_06 : SURF2,
    color: isActive ? NAVY : TEXT_SECONDARY,
    cursor: isClickable ? "pointer" : "default",
    userSelect: "none",
    whiteSpace: "nowrap",
    lineHeight: 1,
    transition: "border-color 100ms, background 100ms",
    ...(color ? {
      background: `${color}18`,
      border: `1px solid ${color}40`,
      color,
    } : {}),
    ...style,
  };

  return (
    <span
      className={className}
      style={baseStyle}
      onClick={onClick}
      role={isClickable ? "button" : undefined}
      tabIndex={isClickable ? 0 : undefined}
      onKeyDown={isClickable ? (e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); onClick(e); } } : undefined}
    >
      {children}
      {onRemove && (
        <button
          type="button"
          onClick={(e) => { e.stopPropagation(); onRemove(); }}
          aria-label="Remove tag"
          style={{
            display: "inline-flex",
            alignItems: "center",
            justifyContent: "center",
            width: 14,
            height: 14,
            borderRadius: 2,
            border: "none",
            background: "transparent",
            cursor: "pointer",
            color: "inherit",
            opacity: 0.6,
            padding: 0,
            lineHeight: 1,
          }}
          onMouseEnter={e => (e.currentTarget.style.opacity = 1)}
          onMouseLeave={e => (e.currentTarget.style.opacity = 0.6)}
        >
          <svg width="8" height="8" viewBox="0 0 8 8" fill="currentColor">
            <path d="M0.646 0.646a.5.5 0 01.708 0L4 3.293l2.646-2.647a.5.5 0 01.708.708L4.707 4l2.647 2.646a.5.5 0 01-.708.708L4 4.707 1.354 7.354a.5.5 0 01-.708-.708L3.293 4 .646 1.354a.5.5 0 010-.708z" />
          </svg>
        </button>
      )}
    </span>
  );
}

/** TagGroup — wraps tags with consistent gap */
export function TagGroup({ children, gap = 4, className = "" }) {
  return (
    <div className={className} style={{ display: "flex", flexWrap: "wrap", gap, alignItems: "center" }}>
      {children}
    </div>
  );
}

export default Tag;
