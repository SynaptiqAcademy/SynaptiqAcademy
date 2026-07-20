import React, { useState, useEffect, useCallback } from "react";
import { NAVY, ACCENT, EMERALD, TEXT_SECONDARY } from "@/lib/tokens";
import { InstitutionLayout } from "@/layouts";
import { Card, StatCard, StatGrid, List, ListItem, Spinner } from "@/components/ds";

const API = process.env.REACT_APP_API_URL || "";
const authH = () => ({ Authorization: `Bearer ${localStorage.getItem("token")}` });

export default function PublicationIntelligence() {
  const [pubs, setPubs] = useState(null);
  const [trends, setTrends] = useState([]);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [pr, tr] = await Promise.all([
        fetch(`${API}/api/iip/publications/overview`, { headers: authH() }),
        fetch(`${API}/api/iip/publications/trends?years=6`, { headers: authH() }),
      ]);
      if (pr.ok) setPubs(await pr.json());
      if (tr.ok) setTrends(await tr.json());
    } catch (_) {}
    setLoading(false);
  }, []);

  useEffect(() => { load(); }, [load]);

  if (loading) return (
    <div style={{ minHeight: "60vh", display: "flex", alignItems: "center", justifyContent: "center" }}>
      <Spinner size={32} color={ACCENT} />
    </div>
  );

  const maxPubs = Math.max(...trends.map(t => t.total), 1);
  const growthPositive = (pubs?.growth_rate_pct || 0) >= 0;

  return (
    <InstitutionLayout
      title="Publication Intelligence"
      subtitle={pubs ? `Growth: ${growthPositive ? "+" : ""}${pubs.growth_rate_pct ?? 0}% year-on-year · ${pubs.total ?? 0} total publications` : "Research output and citation analytics"}
    >
      {/* StatCard has no per-tile value-color override, so the original
          color-coded KPI values are flattened. */}
      <StatGrid cols={6} className="mb-5">
        <StatCard label="Total Publications" value={pubs?.total ?? 0} />
        <StatCard label="Q1/Q2 Publications" value={pubs?.q1q2_count ?? 0} sub={`${pubs?.q1q2_pct ?? 0}% of total`} />
        <StatCard label="Open Access" value={pubs?.open_access_count ?? 0} sub={`${pubs?.open_access_pct ?? 0}%`} />
        <StatCard label="Total Citations" value={pubs?.total_citations ?? 0} />
        <StatCard label="Avg Citations" value={pubs?.avg_citations ?? 0} />
        <StatCard label="Highly Cited (10+)" value={pubs?.high_cited_count ?? 0} />
      </StatGrid>

      {/* Publication trend chart — stacked/overlaid bars (total translucent
          navy with a Q1/Q2 emerald overlay per year) have no equivalent in
          BarChart (single value per bar, no stacking) — left hand-rolled. */}
      {trends.length > 0 && (
        <Card padding="lg" className="mb-4">
          <h3 style={{ margin: "0 0 16px", fontSize: 14, fontWeight: 700, color: NAVY }}>Annual Publication Output</h3>
          <div style={{ display: "flex", alignItems: "flex-end", gap: 8, height: 100 }}>
            {trends.map(t => {
              const h = Math.max(4, (t.total / maxPubs) * 100);
              const q12h = Math.max(0, (t.q1q2 / maxPubs) * 100);
              return (
                <div key={t.year} style={{ flex: 1, display: "flex", flexDirection: "column", alignItems: "center", gap: 4 }}>
                  <div style={{ width: "100%", display: "flex", flexDirection: "column", alignItems: "stretch", height: 100, justifyContent: "flex-end" }}>
                    <div title={`Total: ${t.total}`} style={{ background: `${NAVY}30`, borderRadius: "3px 3px 0 0", height: h, position: "relative" }}>
                      <div title={`Q1/Q2: ${t.q1q2}`} style={{ background: EMERALD, borderRadius: "3px 3px 0 0", height: q12h, position: "absolute", bottom: 0, left: 0, right: 0 }} />
                    </div>
                  </div>
                  <span style={{ fontSize: 10, color: TEXT_SECONDARY }}>{t.year}</span>
                </div>
              );
            })}
          </div>
          <div style={{ display: "flex", gap: 16, marginTop: 10 }}>
            <span style={{ fontSize: 11, color: TEXT_SECONDARY, display: "flex", alignItems: "center", gap: 4 }}>
              <span style={{ display: "inline-block", width: 10, height: 10, background: `${NAVY}30`, borderRadius: 2 }} /> Total
            </span>
            <span style={{ fontSize: 11, color: TEXT_SECONDARY, display: "flex", alignItems: "center", gap: 4 }}>
              <span style={{ display: "inline-block", width: 10, height: 10, background: EMERALD, borderRadius: 2 }} /> Q1/Q2
            </span>
          </div>
        </Card>
      )}

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
        {/* Quartile distribution — per-quartile fixed color mapping (Q1
            emerald/Q2 blue/Q3 amber/other gray) isn't value-based, so
            ProgressBar's colorByValue can't express it — left hand-rolled. */}
        <Card padding="lg">
          <h3 style={{ margin: "0 0 14px", fontSize: 14, fontWeight: 700, color: NAVY }}>Quartile Distribution</h3>
          {Object.entries(pubs?.quartile_distribution || {}).map(([q, count]) => {
            const pct = Math.round(count / (pubs?.total || 1) * 100);
            const color = q === "Q1" ? EMERALD : q === "Q2" ? "#0ea5e9" : q === "Q3" ? "#f59e0b" : "#94a3b8";
            return (
              <div key={q} style={{ marginBottom: 10 }}>
                <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 3 }}>
                  <span style={{ fontSize: 13, color: NAVY, fontWeight: 600 }}>{q}</span>
                  <span style={{ fontSize: 12, color: TEXT_SECONDARY }}>{count} ({pct}%)</span>
                </div>
                <div style={{ height: 6, background: `${NAVY}12`, borderRadius: 99 }}>
                  <div style={{ height: "100%", borderRadius: 99, background: color, width: `${pct}%` }} />
                </div>
              </div>
            );
          })}
        </Card>

        {/* Top journals */}
        <Card padding="lg">
          <h3 style={{ margin: "0 0 14px", fontSize: 14, fontWeight: 700, color: NAVY }}>Top Journals</h3>
          <List>
            {(pubs?.top_journals || []).slice(0, 8).map((j, i) => (
              <ListItem
                key={i}
                compact
                title={j.journal}
                trailing={<span style={{ fontSize: 12, fontWeight: 700, color: TEXT_SECONDARY }}>{j.count}</span>}
              />
            ))}
          </List>
        </Card>
      </div>
    </InstitutionLayout>
  );
}
