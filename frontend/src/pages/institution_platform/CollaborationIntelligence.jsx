import React, { useState, useEffect, useCallback } from "react";
import { Globe } from "lucide-react";
import { NAVY, BRD, ACCENT, TEXT_SECONDARY } from "@/lib/tokens";
import { InstitutionLayout } from "@/layouts";
import { Card, StatCard, StatGrid, Spinner } from "@/components/ds";

const API = process.env.REACT_APP_API_URL || "";
const authH = () => ({ Authorization: `Bearer ${localStorage.getItem("token")}` });

export default function CollaborationIntelligence() {
  const [collab, setCollab] = useState(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const r = await fetch(`${API}/api/iip/collaborations/overview`, { headers: authH() });
      if (r.ok) setCollab(await r.json());
    } catch (_) {}
    setLoading(false);
  }, []);

  useEffect(() => { load(); }, [load]);

  if (loading) return (
    <div style={{ minHeight: "60vh", display: "flex", alignItems: "center", justifyContent: "center" }}>
      <Spinner size={32} color={ACCENT} />
    </div>
  );

  return (
    <InstitutionLayout
      title="Collaboration Intelligence"
      subtitle={`${collab?.international_pct ?? 0}% international · Network density ${collab?.network_density ?? 0}`}
    >
      {/* Note: StatCard's value text is a fixed navy — the per-tile value
          color-coding (emerald/blue/purple/amber) from the original hand-rolled
          tiles has no color-override prop on StatCard, so it is flattened. */}
      <StatGrid cols={5} className="mb-5">
        <StatCard label="Total Collaborations" value={collab?.total ?? 0} />
        <StatCard label="Active" value={collab?.active ?? 0} />
        <StatCard label="International" value={collab?.international ?? 0} />
        <StatCard label="Internal" value={collab?.internal ?? 0} />
        <StatCard label="Avg per Researcher" value={collab?.avg_per_researcher ?? 0} />
      </StatGrid>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
        <Card padding="lg">
          <h3 style={{ margin: "0 0 14px", fontSize: 14, fontWeight: 700, color: NAVY }}>
            <Globe size={14} style={{ marginRight: 6, verticalAlign: "middle" }} color={ACCENT} />
            Top Partner Institutions
          </h3>
          {(collab?.top_partner_institutions || []).length === 0
            ? <p style={{ fontSize: 13, color: TEXT_SECONDARY }}>No external partner data recorded yet.</p>
            : (collab?.top_partner_institutions || []).map((p, i) => (
              <div key={i} style={{ display: "flex", justifyContent: "space-between", padding: "7px 0", borderBottom: `1px solid ${BRD}` }}>
                <span style={{ fontSize: 13, color: NAVY, fontWeight: 500 }}>{p.institution}</span>
                <span style={{ fontSize: 12, fontWeight: 700, color: TEXT_SECONDARY }}>{p.count}</span>
              </div>
            ))}
        </Card>

        <Card padding="lg">
          <h3 style={{ margin: "0 0 14px", fontSize: 14, fontWeight: 700, color: NAVY }}>Collaboration Types</h3>
          {Object.entries(collab?.type_distribution || {}).map(([type, count]) => {
            const total = collab?.total || 1;
            const pct = Math.round(count / total * 100);
            return (
              <div key={type} style={{ marginBottom: 10 }}>
                <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 3 }}>
                  <span style={{ fontSize: 13, color: NAVY, fontWeight: 500 }}>{type.replace(/_/g, " ")}</span>
                  <span style={{ fontSize: 12, color: TEXT_SECONDARY }}>{count} ({pct}%)</span>
                </div>
                {/* Fixed cyan fill is intentional brand color for this metric type —
                    ProgressBar's colorByValue only maps to navy/amber/crimson/emerald
                    by threshold, so it can't express an arbitrary fixed color; left
                    hand-rolled. */}
                <div style={{ height: 5, background: `${NAVY}12`, borderRadius: 99 }}>
                  <div style={{ height: "100%", borderRadius: 99, background: "#06b6d4", width: `${pct}%` }} />
                </div>
              </div>
            );
          })}
          {Object.keys(collab?.type_distribution || {}).length === 0 && (
            <p style={{ fontSize: 13, color: TEXT_SECONDARY }}>No collaboration type data available.</p>
          )}
        </Card>
      </div>
    </InstitutionLayout>
  );
}
