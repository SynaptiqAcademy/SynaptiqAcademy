import React from "react";
import { NAVY, EMERALD, AMBER, CRIMSON, BRDX, TEXT_PRIMARY, TEXT_TERTIARY, TEXT_MUTED, FONT_SERIF, RADIUS_FULL } from "@/lib/tokens";

/**
 * ProgressBar — linear completion indicator.
 *
 * Sizes: sm (4px) | md (8px, default) | lg (12px)
 * colorByValue: if true, color shifts amber >80%, crimson >100%
 */
export function ProgressBar({
  value = 0,          // current
  max = 100,
  label,
  showValue = true,
  valueLabel,         // override value display string
  size = "md",
  colorByValue = false,
  className = "",
}) {
  const pct = Math.min(100, Math.max(0, (value / max) * 100));

  const trackH = { sm: 4, md: 8, lg: 12 }[size] || 8;

  let fillColor = NAVY;
  if (colorByValue) {
    if (pct > 100) fillColor = CRIMSON;
    else if (pct > 80) fillColor = AMBER;
    else if (pct === 100) fillColor = EMERALD;
  }

  const displayValue = valueLabel ?? (max === 100 ? `${Math.round(pct)}%` : `${value} / ${max}`);

  return (
    <div className={className}>
      {(label || showValue) && (
        <div style={{
          display: "flex", alignItems: "center", justifyContent: "space-between",
          marginBottom: 6,
        }}>
          {label && (
            <span style={{ fontSize: "0.75rem", fontWeight: 500, color: TEXT_PRIMARY }}>{label}</span>
          )}
          {showValue && (
            <span style={{ fontSize: "0.72rem", color: TEXT_TERTIARY }}>{displayValue}</span>
          )}
        </div>
      )}
      <div style={{
        width: "100%", height: trackH,
        background: BRDX, borderRadius: RADIUS_FULL, overflow: "hidden",
      }}>
        <div style={{
          height: "100%", width: `${pct}%`,
          background: fillColor, borderRadius: RADIUS_FULL,
          transition: "width 600ms ease-out",
        }} />
      </div>
    </div>
  );
}

/**
 * ProgressRing — circular completion indicator (SVG-based).
 *
 * Sizes: sm (48px) | md (64px, default) | lg (96px)
 */
export function ProgressRing({
  value = 0,
  max = 100,
  label,
  size = "md",
  colorByValue = true,
  className = "",
}) {
  const dim = { sm: 48, md: 64, lg: 96 }[size] || 64;
  const stroke = { sm: 4, md: 4, lg: 6 }[size] || 4;
  const r = (dim - stroke * 2) / 2;
  const circ = 2 * Math.PI * r;
  const pct = Math.min(100, Math.max(0, (value / max) * 100));
  const offset = circ - (pct / 100) * circ;

  let color = NAVY;
  if (colorByValue) {
    if (pct >= 80) color = EMERALD;
    else if (pct >= 50) color = NAVY;
    else if (pct >= 30) color = AMBER;
    else color = CRIMSON;
  }

  const fontSize = { sm: "0.75rem", md: "1rem", lg: "1.4rem" }[size] || "1rem";
  const labelSize = { sm: "0.55rem", md: "0.65rem", lg: "0.75rem" }[size] || "0.65rem";

  return (
    <div className={className} style={{ display: "inline-flex", flexDirection: "column", alignItems: "center", gap: 4 }}>
      <div style={{ position: "relative", width: dim, height: dim }}>
        <svg width={dim} height={dim} viewBox={`0 0 ${dim} ${dim}`} style={{ transform: "rotate(-90deg)" }}>
          {/* Track */}
          <circle cx={dim / 2} cy={dim / 2} r={r} fill="none" stroke={BRDX} strokeWidth={stroke} />
          {/* Fill */}
          <circle
            cx={dim / 2} cy={dim / 2} r={r}
            fill="none" stroke={color} strokeWidth={stroke}
            strokeLinecap="round"
            strokeDasharray={circ}
            strokeDashoffset={offset}
            style={{ transition: "stroke-dashoffset 800ms ease-out, stroke 300ms" }}
          />
        </svg>
        {/* Center */}
        <div style={{
          position: "absolute", inset: 0,
          display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center",
        }}>
          <span style={{ fontFamily: FONT_SERIF, fontSize, fontWeight: 700, color: TEXT_PRIMARY, lineHeight: 1 }}>
            {Math.round(pct)}
          </span>
          <span style={{ fontSize: labelSize, color: TEXT_MUTED, lineHeight: 1, marginTop: 1 }}>/ 100</span>
        </div>
      </div>
      {label && (
        <span style={{ fontSize: "0.68rem", color: TEXT_MUTED, textAlign: "center" }}>{label}</span>
      )}
    </div>
  );
}

export default ProgressBar;
