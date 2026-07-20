/* eslint-disable */
import React from "react";

/**
 * Grid — universal responsive CSS grid.
 *
 * Props:
 *   cols      1|2|3|4|"auto"  column count. "auto" auto-fills at minWidth.
 *   gap       "xs"|"sm"|"md"|"lg"|"xl"  spacing (default: "md")
 *   minWidth  number  px, used with cols="auto" (default: 240)
 *   children  ReactNode
 *
 * Responsive: cols 3+ collapses to 2 on tablet, 1 on mobile via Tailwind.
 * For cols 1/2 we use inline grid directly. For 3/4/"auto" we use Tailwind
 * responsive classes to collapse cleanly.
 */

const GAP_MAP = { xs: 8, sm: 12, md: 16, lg: 24, xl: 32 };

// Tailwind responsive classes for larger column counts
const TAILWIND_COLS = {
  3: "grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3",
  4: "grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4",
};

export function Grid({
  cols = 1,
  gap = "md",
  minWidth = 240,
  children,
  style,
  className = "",
  ...props
}) {
  const g = GAP_MAP[gap] ?? 16;

  // "auto" fill — CSS only
  if (cols === "auto") {
    return (
      <div
        style={{
          display: "grid",
          gridTemplateColumns: `repeat(auto-fill, minmax(${minWidth}px, 1fr))`,
          gap: g,
          ...style,
        }}
        className={className}
        {...props}
      >
        {children}
      </div>
    );
  }

  // 3 or 4 cols — use Tailwind for responsive collapse
  if (cols === 3 || cols === 4) {
    return (
      <div
        className={`${TAILWIND_COLS[cols]} ${className}`}
        style={{ gap: g, ...style }}
        {...props}
      >
        {children}
      </div>
    );
  }

  // 1 or 2 cols — pure inline
  return (
    <div
      style={{
        display: "grid",
        gridTemplateColumns: `repeat(${cols}, 1fr)`,
        gap: g,
        ...style,
      }}
      className={className}
      {...props}
    >
      {children}
    </div>
  );
}

export default Grid;
