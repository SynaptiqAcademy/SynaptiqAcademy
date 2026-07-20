import React from "react";

/**
 * Skeleton — shimmer placeholders for loading states.
 * Uses the .sq-skeleton CSS class (defined in index.css).
 *
 * Replaces: <div className="h-24 bg-slate-200 animate-pulse" /> patterns.
 */

const ROUNDED = { none: "rounded-none", sm: "rounded-sm", md: "rounded", lg: "rounded-lg", full: "rounded-full" };

export function Skeleton({ height = "h-6", width = "w-full", count = 1, rounded = "md", className = "" }) {
  const base = ["sq-skeleton block", height, width, ROUNDED[rounded] ?? ROUNDED.md, className]
    .filter(Boolean).join(" ");
  if (count === 1) return <span className={base} aria-hidden="true" />;
  return <>{Array.from({ length: count }).map((_, i) => <span key={i} className={base} aria-hidden="true" />)}</>;
}

// NOTE: text-line and card-shaped skeletons live in ds/LoadingState.jsx
// (SkeletonLine, SkeletonCard, SkeletonTable, SkeletonPage) — that is the
// one canonical implementation for those shapes. This file owns only the
// base shimmer primitive above.

export default Skeleton;
