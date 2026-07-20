import React from "react";
import { BRD, WHITE, TEXT_MUTED } from "@/lib/tokens";
import { StatCard, StatGrid } from "./StatCard";
import { Sparkline } from "./Chart";

/**
 * ContextPanel — the "N stats, then detail" header every admin page starts with.
 *
 * Props:
 *   stats   [{ label, value, sub, icon, trend, highlight, onClick }]
 *   trend   number[]   optional sparkline data shown alongside the stats
 *   cols    number     StatGrid column count (default 5)
 *   loading bool
 */
export function ContextPanel({ stats = [], trend, cols = 5, loading = false }) {
  return (
    <div style={{
      background: WHITE, border: `1px solid ${BRD}`, borderRadius: 6,
      padding: 16, marginBottom: 20,
      display: "flex", alignItems: "stretch", gap: 16,
    }}>
      <div style={{ flex: 1 }}>
        <StatGrid cols={cols}>
          {stats.map((s, i) => (
            <StatCard
              key={s.label || i}
              label={s.label}
              value={loading ? "…" : s.value}
              sub={s.sub}
              icon={s.icon}
              trend={s.trend}
              highlight={s.highlight}
              onClick={s.onClick}
            />
          ))}
        </StatGrid>
      </div>

      {trend && trend.length > 1 && (
        <div style={{
          flexShrink: 0, display: "flex", flexDirection: "column", justifyContent: "center",
          alignItems: "center", gap: 6, paddingLeft: 16, borderLeft: `1px solid ${BRD}`,
          minWidth: 100,
        }}>
          <Sparkline data={trend} width={90} height={32} />
          <span style={{ fontSize: "0.62rem", color: TEXT_MUTED, fontWeight: 600, letterSpacing: "0.06em", textTransform: "uppercase" }}>
            Trend
          </span>
        </div>
      )}
    </div>
  );
}

export default ContextPanel;
