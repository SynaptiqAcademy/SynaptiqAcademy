/* eslint-disable */
import React from "react";
import { NAVY, EMERALD, AMBER, CRIMSON, TEXT_MUTED, BRD, BRD_SOFT, WARM, CHART_PALETTE, RADIUS_FULL } from "@/lib/tokens";

// ── Shared helpers ─────────────────────────────────────────────────────────────

function normalize(data, min, max) {
  const lo = min ?? Math.min(...data);
  const hi = max ?? Math.max(...data);
  const range = hi - lo || 1;
  return data.map(v => (v - lo) / range);
}

function toPoints(normalized, w, h, padX = 2, padY = 3) {
  const step = (w - padX * 2) / Math.max(normalized.length - 1, 1);
  return normalized.map((v, i) => ({
    x: padX + i * step,
    y: padY + (1 - v) * (h - padY * 2),
  }));
}

function pointsToPath(pts) {
  return pts.map((p, i) => `${i === 0 ? "M" : "L"} ${p.x.toFixed(1)} ${p.y.toFixed(1)}`).join(" ");
}

const PALETTE = CHART_PALETTE;

// ── Sparkline ─────────────────────────────────────────────────────────────────
/**
 * Sparkline — compact inline SVG line chart.
 * Use for KPI cards, table cells, trend indicators.
 *
 * Props:
 *   data      number[]   required
 *   width     number     default 80
 *   height    number     default 28
 *   color     string     auto-derived from trend if omitted
 *   trend     "up"|"down"|"flat"   auto-detected if omitted
 *   min/max   number     optional y-axis clamp
 */
export function Sparkline({ data = [], width = 80, height = 28, color, trend, min, max, style }) {
  if (data.length < 2) return null;
  const effectiveTrend = trend ?? (data[data.length - 1] > data[0] ? "up" : data[data.length - 1] < data[0] ? "down" : "flat");
  const lineColor = color ?? (effectiveTrend === "up" ? EMERALD : effectiveTrend === "down" ? CRIMSON : TEXT_MUTED);
  const norm = normalize(data, min, max);
  const pts = toPoints(norm, width, height);
  const path = pointsToPath(pts);
  const last = pts[pts.length - 1];

  return (
    <svg width={width} height={height} style={{ display: "block", overflow: "visible", ...style }}>
      <path d={path} fill="none" stroke={lineColor} strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
      <circle cx={last.x} cy={last.y} r="2.5" fill={lineColor} />
    </svg>
  );
}

// ── SparkArea ─────────────────────────────────────────────────────────────────
/**
 * SparkArea — Sparkline with filled area beneath the line.
 */
export function SparkArea({ data = [], width = 80, height = 32, color, trend, min, max, style }) {
  if (data.length < 2) return null;
  const effectiveTrend = trend ?? (data[data.length - 1] > data[0] ? "up" : data[data.length - 1] < data[0] ? "down" : "flat");
  const lineColor = color ?? (effectiveTrend === "up" ? EMERALD : effectiveTrend === "down" ? CRIMSON : TEXT_MUTED);
  const norm = normalize(data, min, max);
  const pts = toPoints(norm, width, height);
  const linePath = pointsToPath(pts);
  const areaPath = `${linePath} L ${pts[pts.length - 1].x.toFixed(1)} ${height} L ${pts[0].x.toFixed(1)} ${height} Z`;

  return (
    <svg width={width} height={height} style={{ display: "block", overflow: "visible", ...style }}>
      <path d={areaPath} fill={lineColor} fillOpacity="0.1" />
      <path d={linePath} fill="none" stroke={lineColor} strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

// ── MiniBar ───────────────────────────────────────────────────────────────────
/**
 * MiniBar — single horizontal progress bar. Use for percentage values inside cards.
 *
 * Props:
 *   value     number   current value
 *   max       number   default 100
 *   height    number   default 4
 *   color     string   auto-derived by value if omitted (green/amber/red)
 */
export function MiniBar({ value = 0, max = 100, height = 4, color, style }) {
  const pct = Math.min(100, Math.max(0, (value / max) * 100));
  const barColor = color ?? (pct >= 70 ? EMERALD : pct >= 40 ? AMBER : CRIMSON);

  return (
    <div style={{ height, borderRadius: RADIUS_FULL, background: BRD_SOFT, overflow: "hidden", ...style }}>
      <div style={{
        height: "100%", width: `${pct}%`, background: barColor, borderRadius: RADIUS_FULL,
        transition: "width 500ms cubic-bezier(0.16,1,0.3,1)",
      }} />
    </div>
  );
}

// ── BarChart ──────────────────────────────────────────────────────────────────
/**
 * BarChart — vertical mini bar chart. Good for dashboard widgets.
 *
 * Props:
 *   data        [{ label, value, color? }]
 *   height      number     default 80
 *   gap         number     default 4
 *   color       string     fallback bar color
 *   showValues  bool       show value above bar
 *   showLabels  bool       show label below bar
 */
export function BarChart({ data = [], height = 80, gap = 4, color, showValues = false, showLabels = false, style }) {
  const max = Math.max(...data.map(d => d.value), 1);
  const barColor = color ?? NAVY;

  return (
    <div style={{ display: "flex", alignItems: "flex-end", gap, height: height + (showLabels ? 18 : 0), width: "100%", ...style }}>
      {data.map((d, i) => {
        const pct = (d.value / max) * 100;
        return (
          <div key={i} style={{ flex: 1, display: "flex", flexDirection: "column", alignItems: "center", height: "100%", justifyContent: "flex-end", gap: 3 }}>
            {showValues && <span style={{ fontSize: "0.6rem", color: TEXT_MUTED, lineHeight: 1 }}>{d.value}</span>}
            <div
              style={{
                width: "100%", height: `${pct}%`, minHeight: 2,
                background: d.color ?? barColor,
                borderRadius: "3px 3px 0 0",
                transition: "height 500ms cubic-bezier(0.16,1,0.3,1)",
              }}
              title={`${d.label}: ${d.value}`}
            />
            {showLabels && (
              <span style={{ fontSize: "0.6rem", color: TEXT_MUTED, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis", maxWidth: "100%", textAlign: "center", lineHeight: 1.3 }}>
                {d.label}
              </span>
            )}
          </div>
        );
      })}
    </div>
  );
}

// ── DonutChart ────────────────────────────────────────────────────────────────
/**
 * DonutChart — SVG ring chart for a single percentage.
 * Children are centered inside the ring (use for value/label).
 *
 * Props:
 *   value       number   current value
 *   max         number   default 100
 *   size        number   default 56
 *   strokeWidth number   default 6
 *   color       string   ring color, auto-derived by value if omitted
 *   trackColor  string   background ring color
 */
export function DonutChart({ value = 0, max = 100, size = 56, strokeWidth = 6, color, trackColor, children, style }) {
  const pct = Math.min(100, Math.max(0, (value / max) * 100));
  const r = (size - strokeWidth) / 2;
  const circ = 2 * Math.PI * r;
  const offset = circ - (pct / 100) * circ;
  const ringColor = color ?? (pct >= 70 ? EMERALD : pct >= 40 ? AMBER : CRIMSON);
  const center = size / 2;

  return (
    <div style={{ position: "relative", width: size, height: size, flexShrink: 0, ...style }}>
      <svg width={size} height={size} style={{ transform: "rotate(-90deg)" }}>
        <circle
          cx={center} cy={center} r={r}
          fill="none"
          stroke={trackColor ?? BRD_SOFT}
          strokeWidth={strokeWidth}
        />
        <circle
          cx={center} cy={center} r={r}
          fill="none"
          stroke={ringColor}
          strokeWidth={strokeWidth}
          strokeDasharray={`${circ} ${circ}`}
          strokeDashoffset={offset}
          strokeLinecap="round"
          style={{ transition: "stroke-dashoffset 700ms cubic-bezier(0.16,1,0.3,1)" }}
        />
      </svg>
      {children && (
        <div style={{ position: "absolute", inset: 0, display: "flex", alignItems: "center", justifyContent: "center" }}>
          {children}
        </div>
      )}
    </div>
  );
}

// ── LineChart ─────────────────────────────────────────────────────────────────
/**
 * LineChart — full-width SVG multi-series line chart.
 * Use for dashboard panels and analytics sections.
 *
 * Props:
 *   series      [{ label, data: number[], color? }]
 *   height      number   default 160
 *   min/max     number   y-axis bounds
 *   showGrid    bool     default true
 *   showDots    bool     default false
 */
export function LineChart({ series = [], height = 160, min, max, showGrid = true, showDots = false, style }) {
  if (!series.length || !series[0]?.data?.length) return null;
  const allVals = series.flatMap(s => s.data);
  const lo = min ?? Math.min(...allVals);
  const hi = max ?? Math.max(...allVals);

  const norm = (v) => (v - lo) / (hi - lo || 1);
  const maxLen = Math.max(...series.map(s => s.data.length));

  const PAD = { t: 8, r: 4, b: 4, l: 4 };
  const W = 300;
  const H = height;
  const innerW = W - PAD.l - PAD.r;
  const innerH = H - PAD.t - PAD.b;

  const toCoords = (data) => {
    const step = innerW / Math.max(data.length - 1, 1);
    return data.map((v, i) => ({
      x: PAD.l + i * step,
      y: PAD.t + (1 - norm(v)) * innerH,
    }));
  };

  return (
    <svg viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="none" style={{ width: "100%", height, display: "block", ...style }}>
      {showGrid && [0.25, 0.5, 0.75].map(t => (
        <line
          key={t}
          x1={PAD.l} y1={PAD.t + (1 - t) * innerH}
          x2={W - PAD.r} y2={PAD.t + (1 - t) * innerH}
          stroke={BRD_SOFT} strokeWidth="0.8"
        />
      ))}
      {series.map((s, si) => {
        const pts = toCoords(s.data);
        const lineColor = s.color ?? PALETTE[si % PALETTE.length];
        const path = pointsToPath(pts);
        const areaPath = `${path} L ${pts[pts.length - 1].x.toFixed(1)} ${H} L ${pts[0].x.toFixed(1)} ${H} Z`;

        return (
          <g key={si}>
            <path d={areaPath} fill={lineColor} fillOpacity="0.06" />
            <path d={path} fill="none" stroke={lineColor} strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
            {showDots && pts.map((p, pi) => (
              <circle key={pi} cx={p.x} cy={p.y} r="2" fill={lineColor} />
            ))}
          </g>
        );
      })}
    </svg>
  );
}

// ── Legend ────────────────────────────────────────────────────────────────────
/**
 * Legend — color legend for multi-series charts.
 */
export function ChartLegend({ items = [], style }) {
  return (
    <div style={{ display: "flex", flexWrap: "wrap", gap: "6px 16px", ...style }}>
      {items.map((item, i) => (
        <div key={i} style={{ display: "flex", alignItems: "center", gap: 6 }}>
          <div style={{ width: 10, height: 3, borderRadius: 2, background: item.color ?? PALETTE[i % PALETTE.length], flexShrink: 0 }} />
          <span style={{ fontSize: "0.75rem", color: TEXT_MUTED }}>{item.label}</span>
        </div>
      ))}
    </div>
  );
}
