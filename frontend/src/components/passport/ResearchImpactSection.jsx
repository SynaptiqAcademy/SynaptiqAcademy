import React, { useEffect, useState } from "react";
import { TrendingUp } from "lucide-react";
import { Card } from "@/components/ds/Card";
import api from "@/lib/api";
import { NAVY, EMERALD, TEXT_MUTED, TEXT_SECONDARY, TEXT_PRIMARY, BRD } from "@/lib/tokens";

/** Tiny real-data sparkline — no synthetic points; empty series just renders a flat baseline. */
function Sparkline({ points, color = NAVY }) {
  if (!points || points.length < 2) {
    return <div style={{ height: 32, borderBottom: `1px solid ${BRD}`, marginTop: 8 }} />;
  }
  const w = 100, h = 32;
  const max = Math.max(...points, 1);
  const min = Math.min(...points, 0);
  const range = Math.max(1, max - min);
  const step = w / (points.length - 1);
  const d = points.map((v, i) => `${i === 0 ? "M" : "L"}${i * step},${h - ((v - min) / range) * h}`).join(" ");
  return (
    <svg viewBox={`0 0 ${w} ${h}`} preserveAspectRatio="none" style={{ width: "100%", height: 32, marginTop: 8, display: "block" }}>
      <path d={d} fill="none" stroke={color} strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function KpiTile({ label, value, sub, trend, points }) {
  return (
    <Card padding="lg">
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
        <div style={{ fontSize: 12, fontWeight: 600, color: TEXT_SECONDARY }}>{label}</div>
        {trend && (
          <span style={{ display: "flex", alignItems: "center", gap: 2, fontSize: 11, fontWeight: 700, color: EMERALD }}>
            <TrendingUp size={11} /> {trend}
          </span>
        )}
      </div>
      <div style={{ fontFamily: "Georgia, serif", fontSize: 30, fontWeight: 700, color: TEXT_PRIMARY, marginTop: 6 }}>{value}</div>
      {sub && <div style={{ fontSize: 11.5, color: TEXT_MUTED, marginTop: 2 }}>{sub}</div>}
      <Sparkline points={points} />
    </Card>
  );
}

/**
 * ResearchImpactSection — P1 Phase 7C4.1 §13/§17/§23: two fixes made while
 * redesigning this section.
 * 1. The h-index tile's "Top 5% in Field" caption was a hardcoded string,
 *    not derived from any real data — shown for every user regardless of
 *    their actual standing. Now uses the real percentile from
 *    researchRank.percentile_global (GET /reputation/research/me) when
 *    available, and shows nothing rather than a fabricated claim otherwise.
 * 2. Removed the embedded "Profile Completion" ring + checklist — it
 *    duplicated the one canonical completion experience now on Overview
 *    (PassportCompletion), which is the "no duplicate completion systems"
 *    requirement from the redesign brief.
 */
export function ResearchImpactSection({ impact, researchRank }) {
  const [period, setPeriod] = useState("365d");
  const [series, setSeries] = useState(impact?.citation_growth?.series || null);

  useEffect(() => {
    setSeries(impact?.citation_growth?.series || null);
  }, [impact]);

  const handlePeriodChange = async (e) => {
    const p = e.target.value;
    setPeriod(p);
    try {
      const r = await api.get("/research-impact/citations", { params: { period: p } });
      setSeries(r.data?.series || []);
    } catch { /* keep prior series */ }
  };

  const kpi = impact?.kpi;
  const cumulativePoints = (series || []).map((p) => p.cumulative);
  const percentile = researchRank?.percentile_global;
  const hIndexSub = percentile != null ? `Top ${Math.max(1, 100 - percentile)}% in field` : undefined;

  return (
    <div>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 12, flexWrap: "wrap", gap: 8 }}>
        <div style={{ fontSize: 15, fontWeight: 700, color: TEXT_PRIMARY, letterSpacing: "-0.01em" }}>Research Impact</div>
        <select
          value={period}
          onChange={handlePeriodChange}
          style={{ fontSize: 12, border: `1px solid ${BRD}`, borderRadius: 6, padding: "5px 10px", background: "#fff", color: TEXT_SECONDARY }}
        >
          <option value="365d">This year</option>
          <option value="all">All time</option>
        </select>
      </div>

      {kpi ? (
        <div className="grid grid-cols-2 lg:grid-cols-4" style={{ gap: 14 }}>
          <KpiTile label="h-index" value={kpi.h_index ?? "—"} sub={hIndexSub} />
          <KpiTile
            label="Citations"
            value={(kpi.citations ?? 0).toLocaleString()}
            sub={kpi.cit_pct_30d ? `+${kpi.cit_pct_30d}% this period` : undefined}
            trend={kpi.cit_pct_30d ? `+${kpi.cit_pct_30d}%` : undefined}
            points={cumulativePoints}
          />
          <KpiTile label="i10-index" value={kpi.i10_index ?? "—"} />
          <KpiTile label="Citation Velocity" value={kpi.avg_velocity ?? "—"} sub="Avg. citations / year" />
        </div>
      ) : (
        <Card padding="lg">
          <p style={{ fontSize: 12.5, color: TEXT_MUTED, margin: 0 }}>
            Sync ORCID/OpenAlex to populate your research impact metrics.
          </p>
        </Card>
      )}
    </div>
  );
}

export default ResearchImpactSection;
