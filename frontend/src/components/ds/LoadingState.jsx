import React from "react";
import { NAVY, BRD, BRD_SOFT, WHITE, SURF2, BRDX, TEXT_TERTIARY, RADIUS_SM, RADIUS_MD } from "@/lib/tokens";

/**
 * LoadingState — skeleton loading patterns.
 *
 * Components:
 *   SkeletonLine     — single text/content line
 *   SkeletonCard     — card-shaped skeleton
 *   SkeletonTable    — table-shaped skeleton
 *   SkeletonPage     — full page skeleton (header + cards)
 *   Spinner          — circular spinner
 *   LoadingOverlay   — full-area overlay with spinner
 */

const PULSE = {
  animation: "sq-pulse 1.8s ease-in-out infinite",
};

const STYLE_TAG = `
@keyframes sq-pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.4; }
}
@keyframes sq-spin {
  to { transform: rotate(360deg); }
}
`;

function StyleInjector() {
  return (
    <style
      dangerouslySetInnerHTML={{ __html: STYLE_TAG }}
    />
  );
}

export function SkeletonLine({ width = "100%", height = 14, className = "" }) {
  return (
    <>
      <StyleInjector />
      <div
        className={className}
        style={{
          width,
          height,
          borderRadius: RADIUS_SM,
          background: BRDX,
          ...PULSE,
        }}
      />
    </>
  );
}

export function SkeletonCard({ rows = 3, className = "" }) {
  return (
    <>
      <StyleInjector />
      <div
        className={className}
        style={{
          border: `1px solid ${BRD}`,
          borderRadius: RADIUS_MD,
          background: WHITE,
          padding: "20px 24px",
          display: "flex",
          flexDirection: "column",
          gap: 12,
        }}
      >
        {/* Header skeleton */}
        <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 4 }}>
          <div style={{ width: 36, height: 36, borderRadius: RADIUS_MD, background: BRDX, flexShrink: 0, ...PULSE }} />
          <div style={{ flex: 1, display: "flex", flexDirection: "column", gap: 8 }}>
            <div style={{ height: 14, width: "60%", borderRadius: RADIUS_SM, background: BRDX, ...PULSE }} />
            <div style={{ height: 10, width: "40%", borderRadius: RADIUS_SM, background: BRDX, ...PULSE }} />
          </div>
        </div>
        {/* Content rows */}
        {Array.from({ length: rows }).map((_, i) => (
          <div
            key={i}
            style={{
              height: 12,
              width: i === rows - 1 ? "65%" : "100%",
              borderRadius: RADIUS_SM,
              background: BRDX,
              ...PULSE,
              animationDelay: `${i * 0.1}s`,
            }}
          />
        ))}
      </div>
    </>
  );
}

export function SkeletonTable({ rows = 5, cols = 4, className = "" }) {
  return (
    <>
      <StyleInjector />
      <div className={className} style={{ border: `1px solid ${BRD}`, borderRadius: RADIUS_MD, overflow: "hidden" }}>
        {/* Header */}
        <div
          style={{
            display: "grid",
            gridTemplateColumns: `repeat(${cols}, 1fr)`,
            gap: 12,
            padding: "12px 16px",
            background: SURF2,
            borderBottom: `1px solid ${BRD_SOFT}`,
          }}
        >
          {Array.from({ length: cols }).map((_, i) => (
            <div key={i} style={{ height: 12, borderRadius: RADIUS_SM, background: BRDX, ...PULSE }} />
          ))}
        </div>
        {/* Rows */}
        {Array.from({ length: rows }).map((_, r) => (
          <div
            key={r}
            style={{
              display: "grid",
              gridTemplateColumns: `repeat(${cols}, 1fr)`,
              gap: 12,
              padding: "12px 16px",
              borderBottom: r < rows - 1 ? `1px solid ${BRD_SOFT}` : "none",
            }}
          >
            {Array.from({ length: cols }).map((_, c) => (
              <div
                key={c}
                style={{
                  height: 12,
                  width: c === 0 ? "80%" : c === cols - 1 ? "50%" : "70%",
                  borderRadius: RADIUS_SM,
                  background: BRDX,
                  ...PULSE,
                  animationDelay: `${(r * cols + c) * 0.04}s`,
                }}
              />
            ))}
          </div>
        ))}
      </div>
    </>
  );
}

export function SkeletonPage({ cards = 3, className = "" }) {
  return (
    <>
      <StyleInjector />
      <div className={className} style={{ display: "flex", flexDirection: "column", gap: 24 }}>
        {/* Header skeleton */}
        <div
          style={{
            padding: "28px 32px 24px",
            background: WHITE,
            borderBottom: `1px solid ${BRD}`,
            display: "flex",
            flexDirection: "column",
            gap: 10,
          }}
        >
          <div style={{ height: 22, width: "30%", borderRadius: RADIUS_SM, background: BRDX, ...PULSE }} />
          <div style={{ height: 14, width: "50%", borderRadius: RADIUS_SM, background: BRDX, ...PULSE, animationDelay: "0.1s" }} />
        </div>
        {/* Card grid */}
        <div style={{ padding: "0 24px", display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(280px, 1fr))", gap: 16 }}>
          {Array.from({ length: cards }).map((_, i) => (
            <SkeletonCard key={i} rows={3} />
          ))}
        </div>
      </div>
    </>
  );
}

export function Spinner({ size = 20, color = NAVY, className = "" }) {
  return (
    <>
      <StyleInjector />
      <svg
        className={className}
        width={size}
        height={size}
        viewBox="0 0 24 24"
        fill="none"
        style={{ animation: "sq-spin 700ms linear infinite", display: "inline-block" }}
        aria-label="Loading"
      >
        <circle cx="12" cy="12" r="10" stroke={color} strokeWidth="2.5" strokeOpacity="0.2" />
        <path d="M12 2a10 10 0 0 1 10 10" stroke={color} strokeWidth="2.5" strokeLinecap="round" />
      </svg>
    </>
  );
}

export function LoadingOverlay({ text = "Loading…" }) {
  return (
    <>
      <StyleInjector />
      <div
        style={{
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          flex: 1,
          gap: 14,
          padding: "60px 24px",
        }}
      >
        <Spinner size={28} />
        {text && (
          <p style={{ fontSize: "0.82rem", color: TEXT_TERTIARY, margin: 0 }}>{text}</p>
        )}
      </div>
    </>
  );
}

export default {
  SkeletonLine,
  SkeletonCard,
  SkeletonTable,
  SkeletonPage,
  Spinner,
  LoadingOverlay,
};
