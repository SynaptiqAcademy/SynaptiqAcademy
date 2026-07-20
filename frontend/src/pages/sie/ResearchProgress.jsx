import React, { useState, useEffect, useCallback } from "react";
import { Camera } from "lucide-react";
import { NAVY, WARM, BRD, ACCENT, EMERALD, TEXT_SECONDARY } from "@/lib/tokens";
import { AIWorkspaceLayout } from "@/layouts";
import { SIE_NAV_ITEMS } from "@/lib/navItems";
import { Card, Button, StatCard, StatGrid, DataTable, EmptyState, Spinner, MiniBar as DsMiniBar, H4 } from "@/components/ds";

const API = process.env.REACT_APP_API_URL || "";
const authH = () => ({ Authorization: `Bearer ${localStorage.getItem("token")}` });

function MiniBar({ label, value, color }) {
  return (
    <div style={{ marginBottom: 12 }}>
      <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 4 }}>
        <span style={{ fontSize: 12, color: NAVY, fontWeight: 500 }}>{label}</span>
        <span style={{ fontSize: 12, fontWeight: 700, color: color || ACCENT }}>{value}%</span>
      </div>
      <DsMiniBar value={value} color={color || ACCENT} height={6} />
    </div>
  );
}

export default function ResearchProgress() {
  const [overview, setOverview] = useState(null);
  const [loading, setLoading] = useState(true);
  const [snapping, setSnapping] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const r = await fetch(`${API}/api/sie/progress/overview`, { headers: authH() });
      if (r.ok) setOverview(await r.json());
    } catch (_) {}
    setLoading(false);
  }, []);

  useEffect(() => { load(); }, [load]);

  const takeSnapshot = async () => {
    setSnapping(true);
    await fetch(`${API}/api/sie/progress/snapshot`, { method: "POST", headers: authH() });
    setSnapping(false);
    load();
  };

  if (loading) return (
    <AIWorkspaceLayout title="Research Progress" navItems={SIE_NAV_ITEMS}>
      <div style={{ minHeight: "60vh", display: "flex", alignItems: "center", justifyContent: "center" }}>
        <Spinner size={32} color={ACCENT} />
      </div>
    </AIWorkspaceLayout>
  );

  const s = overview?.summary || {};
  const history = overview?.history || [];
  const maxPubs = Math.max(...history.map(h => h.pubs || 0), 1);

  return (
    <AIWorkspaceLayout
      title="Research Progress"
      subtitle={`Cross-platform activity snapshot · ${overview?.generated_at?.slice(0, 10) || ""}`}
      navItems={SIE_NAV_ITEMS}
      actions={
        <Button onClick={takeSnapshot} loading={snapping} disabled={snapping} size="sm">
          {!snapping && <Camera size={13} />}
          Save Snapshot
        </Button>
      }
    >

      {/* Key metrics grid */}
      <div style={{ marginBottom: 24 }}>
        <StatGrid cols={4}>
          <StatCard label="Total Publications" value={s.publications_total ?? 0} sub={`+${s.publications_this_year ?? 0} this year`} />
          <StatCard label="Grant Success" value={`${s.grant_success_rate_pct ?? 0}%`} sub={`${s.grants_approved}/${s.grants_total} approved`} />
          <StatCard label="Goal Progress" value={`${s.avg_goal_progress_pct ?? 0}%`} sub={`${s.active_goals} active goals`} />
          <StatCard label="Mission Rate" value={`${s.mission_completion_rate_pct ?? 0}%`} sub={`${s.completed_missions}/${s.total_missions} done`} />
        </StatGrid>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 20 }}>
        {/* Progress bars */}
        <Card padding="lg">
          <H4 style={{ marginBottom: 16 }}>Activity Overview</H4>
          <MiniBar label="Goal Completion Rate" value={s.goal_completion_rate_pct ?? 0} color={ACCENT} />
          <MiniBar label="Mission Completion Rate" value={s.mission_completion_rate_pct ?? 0} color={EMERALD} />
          <MiniBar label="Grant Success Rate" value={s.grant_success_rate_pct ?? 0} color="#f59e0b" />
          <MiniBar label="Integrity Score" value={s.integrity_score ?? 0} color="#8b5cf6" />

          <div style={{ marginTop: 14, paddingTop: 14, borderTop: `1px solid ${BRD}` }}>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 6 }}>
              {[
                { label: "Total Collaborations", value: s.collaborations_total ?? 0 },
                { label: "Pub Growth %", value: `${s.publication_growth_pct >= 0 ? "+" : ""}${s.publication_growth_pct ?? 0}%` },
                { label: "Pending Missions", value: s.pending_missions ?? 0 },
                { label: "AI Memory", value: s.memory_configured ? "Active" : "Not set" },
              ].map(({ label, value }) => (
                <div key={label} style={{ background: WARM, borderRadius: 8, padding: "8px 10px" }}>
                  <div style={{ fontSize: 11, color: TEXT_SECONDARY }}>{label}</div>
                  <div style={{ fontSize: 14, fontWeight: 700, color: NAVY }}>{value}</div>
                </div>
              ))}
            </div>
          </div>
        </Card>

        {/* History chart */}
        <Card padding="lg">
          <H4 style={{ marginBottom: 12 }}>Historical Snapshots</H4>
          {history.length === 0 ? (
            <EmptyState
              title="No snapshots yet"
              description="Save a snapshot to start tracking progress over time."
              size="sm"
            />
          ) : (
            <div>
              {/* Bar strip: kept hand-rolled — ds/BarChart has no per-bar
                  title tooltip or progressive-opacity fade, both used here */}
              <div style={{ display: "flex", alignItems: "flex-end", gap: 8, height: 100, marginBottom: 8 }}>
                {history.slice(-10).map((h, i) => {
                  const barH = Math.max(4, (h.pubs / maxPubs) * 100);
                  return (
                    <div key={i} style={{ flex: 1, display: "flex", flexDirection: "column", alignItems: "center", gap: 2 }}>
                      <div title={`${h.date}: ${h.pubs} pubs`} style={{ width: "100%", height: barH, background: ACCENT, borderRadius: "3px 3px 0 0", opacity: 0.6 + (i / history.length) * 0.4 }} />
                      <span style={{ fontSize: 9, color: TEXT_SECONDARY }}>{h.date?.slice(5)}</span>
                    </div>
                  );
                })}
              </div>
              <div style={{ fontSize: 11, color: TEXT_SECONDARY, textAlign: "center", marginBottom: 12 }}>Publications per snapshot</div>
              <DataTable
                columns={[
                  { key: "date", label: "Date", render: (v) => <span style={{ color: TEXT_SECONDARY }}>{v}</span> },
                  { key: "pubs", label: "Pubs", render: (v) => <span style={{ fontWeight: 700, color: NAVY }}>{v}</span> },
                  { key: "goals_progress", label: "Goal Prog", render: (v) => <span style={{ color: ACCENT }}>{v}%</span> },
                  { key: "missions_completed", label: "Missions Done", render: (v) => <span style={{ color: EMERALD }}>{v}</span> },
                ]}
                rows={history.slice(-5).reverse().map((h, i) => ({ id: i, ...h }))}
              />
            </div>
          )}
        </Card>
      </div>
    </AIWorkspaceLayout>
  );
}
