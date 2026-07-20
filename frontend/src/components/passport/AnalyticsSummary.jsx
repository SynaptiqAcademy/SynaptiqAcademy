import React from "react";
import { Link } from "react-router-dom";
import { BarChart3, GraduationCap, ArrowRight } from "lucide-react";
import { Card } from "@/components/ds/Card";
import { StatCard } from "@/components/ds/StatCard";
import { TYPE, NAVY, TEXT_MUTED } from "@/lib/tokens";

// StatGrid's minmax(800/cols, 1fr) assumes a wide multi-column dashboard —
// too wide for this narrow rail widget, so a plain responsive grid is used
// here instead (see StatGrid in components/ds/StatCard.jsx).
const railGrid = { display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(120px, 1fr))", gap: 12 };

/**
 * AnalyticsSummary — compact Research + Teaching analytics summary,
 * linking out to the existing full dashboards rather than rebuilding them.
 */
export function AnalyticsSummary({ reputation, teachingStats }) {
  const hIndex = reputation?.publication?.h_index ?? 0;
  const citations = reputation?.publication?.external_citations ?? 0;
  const showTeaching = !!teachingStats;

  return (
    <Card padding="xl">
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 16 }}>
        <div style={{ ...TYPE.section }}>Research & Teaching Analytics</div>
      </div>

      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 10 }}>
        <span style={{ fontSize: 12.5, fontWeight: 600, display: "flex", alignItems: "center", gap: 6 }}>
          <BarChart3 size={13} style={{ color: NAVY }} /> Research
        </span>
        <Link to="/analytics" style={{ fontSize: 11.5, color: TEXT_MUTED, display: "flex", alignItems: "center", gap: 3, textDecoration: "none" }}>
          View full analytics <ArrowRight size={11} />
        </Link>
      </div>
      <div style={{ ...railGrid, marginBottom: 20 }}>
        <StatCard label="h-index" value={hIndex || "—"} sub="Research impact" />
        <StatCard label="Citations" value={citations ? citations.toLocaleString() : "—"} sub="From OpenAlex" />
      </div>

      {showTeaching && (
        <>
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 10 }}>
            <span style={{ fontSize: 12.5, fontWeight: 600, display: "flex", alignItems: "center", gap: 6 }}>
              <GraduationCap size={13} style={{ color: NAVY }} /> Teaching (30d)
            </span>
            <Link to="/teaching/analytics" style={{ fontSize: 11.5, color: TEXT_MUTED, display: "flex", alignItems: "center", gap: 3, textDecoration: "none" }}>
              View full analytics <ArrowRight size={11} />
            </Link>
          </div>
          <div style={railGrid}>
            <StatCard label="Lessons" value={teachingStats?.period_counts?.lessons ?? 0} />
            <StatCard label="Assessments" value={teachingStats?.period_counts?.assessments ?? 0} />
            <StatCard label="AI Sessions" value={teachingStats?.period_counts?.ai_sessions ?? 0} />
            <StatCard label="Teaching Rep" value={teachingStats?.reputation?.teaching_score ?? 0} />
          </div>
        </>
      )}
    </Card>
  );
}

export default AnalyticsSummary;
