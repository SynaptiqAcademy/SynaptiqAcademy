import React from "react";
import { Link } from "react-router-dom";
import { LineChart, DollarSign, Users2, ArrowRight } from "lucide-react";
import { AnalyticsSummary } from "@/components/passport/AnalyticsSummary";
import { SectionShell } from "@/components/passport/PassportUI";
import { Card } from "@/components/ds/Card";
import { TEXT_SECONDARY, TEXT_PRIMARY } from "@/lib/tokens";

function ExploreCard({ icon: Icon, label, description, to }) {
  return (
    <Card to={to} padding="lg">
      <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
        <div style={{ width: 30, height: 30, borderRadius: 8, background: "rgba(15,40,71,0.08)", display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0 }}>
          <Icon size={14} color="#0F2847" />
        </div>
        <div style={{ minWidth: 0, flex: 1 }}>
          <div style={{ fontSize: 12.5, fontWeight: 700, color: TEXT_PRIMARY }}>{label}</div>
          <div style={{ fontSize: 11, color: TEXT_SECONDARY }}>{description}</div>
        </div>
        <ArrowRight size={13} color={TEXT_SECONDARY} />
      </div>
    </Card>
  );
}

/**
 * AnalyticsTab — the real h-index/citations/teaching summary (AnalyticsSummary,
 * already built and previously unused), plus real navigation into the
 * dedicated full dashboards for deeper analysis. AI Insights lives in the
 * always-visible right rail rather than duplicated here — same component,
 * shown once. "Downloads" isn't tracked anywhere in the backend for
 * publications, so it's honestly left out rather than fabricated.
 */
export function AnalyticsTab({ reputation, teachingStats }) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
      <AnalyticsSummary reputation={reputation} teachingStats={teachingStats} />

      <SectionShell title="Explore Deeper" subtitle="Full dashboards for citations, funding, and collaborations">
        <div className="grid grid-cols-1 sm:grid-cols-3" style={{ gap: 12 }}>
          <ExploreCard icon={LineChart} label="Citation Monitoring" description="Trends & alerts" to="/citations" />
          <ExploreCard icon={DollarSign} label="Funding Analytics" description="Grants & awards" to="/funding" />
          <ExploreCard icon={Users2} label="Collaboration Network" description="Active partners" to="/collaborations" />
        </div>
      </SectionShell>
    </div>
  );
}

export default AnalyticsTab;
