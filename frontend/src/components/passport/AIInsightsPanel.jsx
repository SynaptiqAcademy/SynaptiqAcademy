import React, { useEffect, useState } from "react";
import { Sparkles, Activity, TrendingUp } from "lucide-react";
import { Card } from "@/components/ds/Card";
import { Section } from "@/components/ds/Section";
import { Badge } from "@/components/ds/Badge";
import { EmptyState } from "@/components/ds/EmptyState";
import { SkeletonCard } from "@/components/ds/LoadingState";
import RecommendationCard from "@/components/proactive/RecommendationCard";
import { getBriefing, getRecommendations, getHealthScore, getOpportunityScore } from "@/services/proactiveEngine";
import { TYPE, NAVY, WARM, BRD, TEXT_SECONDARY } from "@/lib/tokens";

/**
 * AIInsightsPanel — inline, evidence-grounded AI insights for the passport
 * page. Reuses the same proactiveEngine data service as the global floating
 * advisor (ProactivePanel), but rendered inline instead of as a second
 * floating widget.
 */
export function AIInsightsPanel() {
  const [briefing, setBriefing] = useState(null);
  const [recs, setRecs] = useState([]);
  const [health, setHealth] = useState(null);
  const [opportunity, setOpportunity] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([getBriefing(), getRecommendations({ limit: 3 }), getHealthScore(), getOpportunityScore()])
      .then(([b, r, h, o]) => {
        setBriefing(b);
        setRecs(r?.recommendations || []);
        setHealth(h);
        setOpportunity(o);
      })
      .finally(() => setLoading(false));
  }, []);

  return (
    <Card padding="xl">
      <Section
        title="AI Insights"
        action={<Badge variant="info" size="sm">NEW</Badge>}
        gap="md"
      >
        {loading && <SkeletonCard rows={2} />}

        {!loading && (
          <>
            <div style={{ display: "flex", gap: 10, marginBottom: 16, flexWrap: "wrap" }}>
              {health != null && (
                <div style={{ display: "flex", alignItems: "center", gap: 9, background: WARM, border: `1px solid ${BRD}`, borderRadius: 10, padding: "8px 12px", flex: "1 1 120px" }}>
                  <span style={{ width: 26, height: 26, borderRadius: 8, background: "rgba(15,40,71,0.08)", display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0 }}>
                    <Activity size={13} style={{ color: NAVY }} />
                  </span>
                  <div>
                    <div style={{ fontSize: 16, fontWeight: 700 }}>{health.score}</div>
                    <div style={{ fontSize: 10, color: TEXT_SECONDARY }}>Research Health · {health.label}</div>
                  </div>
                </div>
              )}
              {opportunity != null && (
                <div style={{ display: "flex", alignItems: "center", gap: 9, background: WARM, border: `1px solid ${BRD}`, borderRadius: 10, padding: "8px 12px", flex: "1 1 120px" }}>
                  <span style={{ width: 26, height: 26, borderRadius: 8, background: "rgba(15,40,71,0.08)", display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0 }}>
                    <TrendingUp size={13} style={{ color: NAVY }} />
                  </span>
                  <div>
                    <div style={{ fontSize: 16, fontWeight: 700 }}>{opportunity.total_open_items}</div>
                    <div style={{ fontSize: 10, color: TEXT_SECONDARY }}>Open Opportunities</div>
                  </div>
                </div>
              )}
            </div>

            {briefing && (
              <div style={{ marginBottom: 16 }}>
                <p style={{ fontSize: 12.5, color: TEXT_SECONDARY, lineHeight: 1.6, margin: 0 }}>
                  {briefing.greeting} — {briefing.date}
                </p>
                {(briefing.summary_items || []).length > 0 && (
                  <ul style={{ margin: "8px 0 0", paddingLeft: 18, fontSize: 12, color: TEXT_SECONDARY }}>
                    {briefing.summary_items.map((item) => (
                      <li key={item.type}>{item.count} {item.label}</li>
                    ))}
                  </ul>
                )}
              </div>
            )}

            {recs.length === 0 ? (
              <EmptyState icon={<Sparkles />} title="No new recommendations right now" />
            ) : (
              <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
                {recs.map((rec) => <RecommendationCard key={rec.id} rec={rec} compact />)}
              </div>
            )}
          </>
        )}
      </Section>
    </Card>
  );
}

export default AIInsightsPanel;
