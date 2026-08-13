import React from "react";
import { WHITE } from "@/lib/tokens";

/**
 * HeroRing — circular progress/score indicator for navy PageLayout heroes.
 * Extracted from components/passport/PassportHero.jsx's TrustRing so every
 * hero with a real score (Trust Score, Reputation, Credits...) renders it
 * identically. Only mounted when a page passes a real `ring` value — never
 * shown as a placeholder.
 */
export function HeroRing({ value, max = 100, label, sublabel, color = "#38BDF8", dim = 84, stroke = 6 }) {
  const r = (dim - stroke) / 2;
  const circ = 2 * Math.PI * r;
  const pct = max > 0 ? Math.min(100, Math.max(0, (value / max) * 100)) : 0;
  const offset = circ - (pct / 100) * circ;
  return (
    <div style={{ textAlign: "center", flexShrink: 0 }}>
      <div style={{ position: "relative", width: dim, height: dim }}>
        <svg width={dim} height={dim} viewBox={`0 0 ${dim} ${dim}`} style={{ transform: "rotate(-90deg)" }}>
          <circle cx={dim / 2} cy={dim / 2} r={r} fill="none" stroke="rgba(255,255,255,0.15)" strokeWidth={stroke} />
          <circle
            cx={dim / 2} cy={dim / 2} r={r} fill="none" stroke={color} strokeWidth={stroke}
            strokeLinecap="round" strokeDasharray={circ} strokeDashoffset={offset}
            style={{ transition: "stroke-dashoffset 800ms ease-out" }}
          />
        </svg>
        <div style={{ position: "absolute", inset: 0, display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center" }}>
          <span style={{ fontFamily: "Georgia, serif", fontSize: 22, fontWeight: 700, color: WHITE, lineHeight: 1 }}>{Math.round(value)}</span>
          {max !== 100 || sublabel ? (
            <span style={{ fontSize: 9.5, color: "rgba(255,255,255,0.5)" }}>{sublabel ?? `/${max}`}</span>
          ) : (
            <span style={{ fontSize: 9.5, color: "rgba(255,255,255,0.5)" }}>/100</span>
          )}
        </div>
      </div>
      {label && (
        <div style={{ fontSize: 10, color: "rgba(255,255,255,0.55)", marginTop: 8, textTransform: "uppercase", letterSpacing: "0.08em" }}>
          {label}
        </div>
      )}
    </div>
  );
}

export default HeroRing;
