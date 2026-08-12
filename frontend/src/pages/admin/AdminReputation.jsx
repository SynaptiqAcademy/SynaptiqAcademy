/**
 * AdminReputation — Reputation system analytics dashboard (admin only).
 *
 * Shows: score distribution by level, badge distribution, top contributors,
 * stale score count. No manual score editing — read-only audit view.
 */
import React, { useEffect, useState } from "react";
import api from "../../lib/api";
import { Award, Users, BarChart2, RefreshCw, Shield } from "lucide-react";
import { getLevel } from "../../hooks/useReputation";
import { NAVY } from "@/lib/tokens";
import { AdministrationLayout } from "@/layouts";
import { Card, Button, Input, StatCard, StatGrid, ProgressBar, Badge, SkeletonCard } from "@/components/ds";

export default function AdminReputation() {
  const [data, setData]     = useState(null);
  const [loading, setLoading] = useState(true);
  const [recalcId, setRecalcId] = useState("");
  const [recalcResult, setRecalcResult] = useState(null);
  const [recalcing, setRecalcing] = useState(false);

  const load = async () => {
    setLoading(true);
    try {
      const { data: d } = await api.get("/reputation/admin/distribution");
      setData(d);
    } catch (e) {
      console.error("Failed to load reputation admin data", e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []);

  const handleRecalc = async () => {
    if (!recalcId.trim()) return;
    setRecalcing(true);
    setRecalcResult(null);
    try {
      const { data: r } = await api.post(`/reputation/admin/recalculate/${recalcId.trim()}`);
      setRecalcResult({ ok: true, overall: r.overall });
    } catch (e) {
      setRecalcResult({ ok: false, msg: e?.response?.data?.detail || "Failed" });
    } finally {
      setRecalcing(false);
    }
  };

  if (loading) return <div className="p-6"><SkeletonCard rows={4} /></div>;
  if (!data)   return <div className="text-sm font-mono text-slate-500">No data available.</div>;

  const totalScored = data.total_with_scores || 0;
  const stale       = data.stale_scores_7d || 0;
  const scoreDist   = data.score_distribution || [];
  const badgeDist   = data.badge_distribution || [];
  const topUsers    = data.top_contributors  || [];

  return (
    <AdministrationLayout
      title="Reputation Analytics"
      subtitle="Read-only audit of the platform-wide reputation system. Scores derive entirely from verified platform activity. No manual score editing is possible."
    >
      <div className="flex flex-col gap-8">
        {/* Summary stats */}
        <StatGrid cols={3}>
          <StatCard label="Users with scores" value={totalScored.toLocaleString()} />
          <StatCard label="Stale (>7 days)" value={stale.toLocaleString()} sub="Scores older than 7 days" />
          <StatCard label="Badges awarded" value={badgeDist.reduce((a, b) => a + b.count, 0).toLocaleString()} />
        </StatGrid>

        {/* Score distribution */}
        <section>
          <h2 className="font-serif text-2xl text-slate-900 mb-5 border-b border-slate-200 pb-3">Score Distribution</h2>
          <div className="space-y-3">
            {scoreDist.length === 0 && <div className="text-sm text-slate-500">No score data yet.</div>}
            {scoreDist.map((row) => {
              const pct = totalScored > 0 ? Math.round((row.count / totalScored) * 100) : 0;
              return (
                <ProgressBar
                  key={row._id}
                  label={row._id}
                  value={row.count}
                  max={totalScored || 1}
                  valueLabel={`${row.count} users (${pct}%)`}
                />
              );
            })}
          </div>
        </section>

        {/* Badge distribution */}
        <section>
          <h2 className="font-serif text-2xl text-slate-900 mb-5 border-b border-slate-200 pb-3">Badge Distribution</h2>
          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-3">
            {badgeDist.length === 0 && <div className="text-sm text-slate-500 col-span-full">No badges awarded yet.</div>}
            {badgeDist.slice(0, 18).map((row) => (
              <Card key={row._id} padding="md" className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Award size={13} strokeWidth={1.5} className="text-[#0F2847] shrink-0" />
                  <span className="text-sm text-slate-900 font-medium">{row._id?.replace(/_/g, " ") || "—"}</span>
                </div>
                <span className="font-mono text-slate-500 text-sm">{row.count}</span>
              </Card>
            ))}
          </div>
        </section>

        {/* Top contributors */}
        <section>
          <h2 className="font-serif text-2xl text-slate-900 mb-5 border-b border-slate-200 pb-3">Top Contributors</h2>
          <Card padding="none" className="divide-y divide-slate-100">
            {topUsers.length === 0 && (
              <div className="px-6 py-4 text-sm text-slate-500">No data yet.</div>
            )}
            {topUsers.map((u, i) => {
              const level = getLevel(u.overall);
              return (
                <div key={u.user_id || i} className="px-6 py-4 flex items-center gap-4">
                  <span className="font-mono text-slate-400 w-5 text-xs">{i + 1}</span>
                  <div className="flex-1 min-w-0">
                    <div className="font-medium text-slate-900 truncate">{u.full_name || "—"}</div>
                    <div className="text-xs text-slate-500 truncate">{u.institution || ""}</div>
                  </div>
                  <div className="text-right shrink-0">
                    <div className="font-serif text-xl text-slate-900">{Math.round(u.overall)}</div>
                    <span className={`overline border px-1.5 py-0.5 text-[10px] ${level.tone}`}>{level.short}</span>
                  </div>
                  <div className="hidden sm:flex flex-col items-end gap-0.5 text-[10px] font-mono text-slate-400 shrink-0 w-28">
                    <span>R {Math.round(u.research_score || 0)}</span>
                    <span>T {Math.round(u.teaching_score || 0)}</span>
                    <span>C {Math.round(u.community_score || 0)}</span>
                  </div>
                </div>
              );
            })}
          </Card>
        </section>

        {/* Manual recalculate (admin audit tool) */}
        <Card padding="lg" as="section">
          <div className="flex items-center gap-2 mb-1">
            <Shield size={14} strokeWidth={1.5} className="text-[#0F2847]" />
            <h2 className="overline">Force Recalculate User</h2>
          </div>
          <p className="text-xs text-slate-500 mb-4">
            Trigger an immediate score recalculation for a specific user. Admins may only audit — scores cannot be manually edited.
          </p>
          <div className="flex items-center gap-3">
            <Input
              value={recalcId}
              onChange={(e) => setRecalcId(e.target.value)}
              placeholder="User ID (MongoDB ObjectId)"
              className="font-mono"
              wrapperClassName="flex-1 !mb-0"
            />
            <Button variant="primary" onClick={handleRecalc} disabled={recalcing || !recalcId.trim()} loading={recalcing}>
              <RefreshCw size={13} strokeWidth={1.5} className={recalcing ? "animate-spin" : ""} />
              {recalcing ? "Recalculating…" : "Recalculate"}
            </Button>
          </div>
          {recalcResult && (
            <div className={`mt-3 text-sm font-mono ${recalcResult.ok ? "text-emerald-700" : "text-red-600"}`}>
              {recalcResult.ok
                ? `Recalculated. New overall score: ${recalcResult.overall}`
                : `Error: ${recalcResult.msg}`}
            </div>
          )}
        </Card>
      </div>
    </AdministrationLayout>
  );
}
