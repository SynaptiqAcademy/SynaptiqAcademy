import React, { useState, useCallback } from "react";
import { Link, useParams } from "react-router-dom";
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  BarChart, Bar,
} from "recharts";
import {
  ArrowLeft, ExternalLink, BookOpen, TrendingUp, Bell, CheckCircle2,
  AlertCircle, Zap, Award, RefreshCw, Info, GitBranch, Users,
  ChevronRight,
} from "lucide-react";
import api from "../lib/api";
import { usePublicationDetail } from "../hooks/useCitations";
import { useCitationSync } from "../hooks/useCitations";
import { TID } from "../lib/testIds";
import { NAVY } from "@/lib/tokens";
import { SkeletonCard } from "@/components/ds/LoadingState";

// ─────────────────────────── primitives ──────────────────────────────────────

function ChartTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null;
  return (
    <div className="border border-slate-200 bg-white shadow-sm px-3 py-2 text-xs">
      <div className="font-medium text-slate-900 mb-1">{label}</div>
      {payload.map((p) => (
        <div key={p.dataKey} className="flex items-center gap-2 text-slate-600">
          <span className="w-2 h-2 rounded-full inline-block" style={{ background: p.stroke || p.fill }} />
          {p.name}: <span className="font-medium text-slate-800">{p.value}</span>
        </div>
      ))}
    </div>
  );
}

function DataNote({ children }) {
  return (
    <div className="flex items-start gap-2 border border-amber-100 bg-amber-50 p-3 text-xs text-amber-800">
      <Info size={12} className="shrink-0 mt-0.5 text-amber-600" />
      <span>{children}</span>
    </div>
  );
}

function SectionHeader({ label, icon: Icon, action }) {
  return (
    <div className="flex items-center justify-between mb-4">
      <div className="flex items-center gap-2">
        {Icon && <Icon size={14} strokeWidth={1.5} className="text-slate-500" />}
        <h2 className="overline">{label}</h2>
      </div>
      {action}
    </div>
  );
}

const ALERT_META = {
  new_citation:  { label: "New Citation",   color: "#2563eb" },
  milestone:     { label: "Milestone",      color: "#16a34a" },
  highly_cited:  { label: "Highly Cited",   color: "#7c3aed" },
  velocity:      { label: "High Velocity",  color: "#d97706" },
  rapid_growth:  { label: "Rapid Growth",   color: "#dc2626" },
  emerging_topic:{ label: "Emerging",       color: "#0891b2" },
  top_performer: { label: "Top Performer",  color: "#16a34a" },
  high_velocity: { label: "High Velocity",  color: "#d97706" },
};

function AlertBadge({ type }) {
  const meta = ALERT_META[type] || { label: type, color: "#64748b" };
  return (
    <span className="text-xs border px-1.5 py-0.5 font-mono whitespace-nowrap"
      style={{ borderColor: meta.color, color: meta.color }}>
      {meta.label}
    </span>
  );
}

// ─────────────────────────── transparent impact breakdown ────────────────────

function ImpactBreakdown({ impact }) {
  if (!impact) return null;
  const components = Object.values(impact.components || {});
  return (
    <div className="space-y-4">
      <div className="flex items-center gap-4">
        <div className="text-center shrink-0">
          <div className="font-serif text-5xl text-[#0F2847] tracking-tight">{impact.score}</div>
          <div className="text-xs text-slate-400 mt-0.5">/ 100</div>
        </div>
        <div>
          <div className="font-medium text-slate-900 text-sm">Publication Impact Score</div>
          <div className="text-xs text-slate-500 mt-0.5 font-mono">{impact.formula}</div>
          {impact.velocity != null && (
            <div className="text-xs text-slate-500 mt-1">
              <span className="font-mono">{impact.velocity}</span> citations/year ·{" "}
              {impact.growth_rate !== 0 && (
                <span className={impact.growth_rate > 0 ? "text-green-600" : "text-red-500"}>
                  {impact.growth_rate > 0 ? "+" : ""}{impact.growth_rate}% growth
                </span>
              )}
            </div>
          )}
        </div>
      </div>
      <div className="space-y-3">
        {components.map((c) => (
          <div key={c.label}>
            <div className="flex items-center justify-between mb-1">
              <span className="text-xs font-medium text-slate-700">{c.label}</span>
              <span className="text-xs font-mono text-slate-500">
                {Math.round(c.weight * 100)}% · {c.contribution} pts
              </span>
            </div>
            <div className="h-1.5 bg-slate-100 relative mb-1">
              <div className="absolute inset-y-0 left-0 bg-[#0F2847] transition-all"
                style={{ width: `${Math.min(100, c.value)}%`, opacity: c.weight + 0.3 }} />
            </div>
            <div className="text-xs text-slate-400">{c.reasoning}</div>
          </div>
        ))}
      </div>
    </div>
  );
}

// ─────────────────────────── velocity gauge ──────────────────────────────────

function VelocityGauge({ velocity, growthRate, recentDelta }) {
  const level =
    velocity >= 20   ? { label: "High Velocity",   color: "#16a34a", pct: 90 } :
    velocity >= 10   ? { label: "Active",           color: "#2563eb", pct: 65 } :
    velocity >= 3    ? { label: "Moderate",         color: "#d97706", pct: 40 } :
    velocity >= 0.5  ? { label: "Low Activity",     color: "#64748b", pct: 20 } :
                       { label: "No Recent Growth", color: "#cbd5e1", pct: 5  };
  return (
    <div className="border border-slate-200 bg-white p-5">
      <div className="overline mb-3">Citation Velocity</div>
      <div className="flex items-end gap-3 mb-3">
        <div className="font-serif text-4xl text-slate-900">{velocity}</div>
        <div className="text-sm text-slate-500 mb-1">citations / year</div>
      </div>
      <div className="h-2 bg-slate-100 relative mb-3">
        <div className="absolute inset-y-0 left-0 transition-all"
          style={{ width: `${level.pct}%`, background: level.color }} />
      </div>
      <div className="flex items-center justify-between text-xs">
        <span style={{ color: level.color }} className="font-mono">{level.label}</span>
        {recentDelta > 0 && (
          <span className="text-green-600 font-mono">+{recentDelta} recent</span>
        )}
      </div>
      {growthRate !== 0 && (
        <div className={`text-xs mt-2 font-mono ${growthRate > 0 ? "text-green-600" : "text-red-500"}`}>
          {growthRate > 0 ? "+" : ""}{growthRate}% growth rate since last snapshot
        </div>
      )}
    </div>
  );
}

// ─────────────────────────── main page ───────────────────────────────────────

export default function CitationDetail() {
  const { id }   = useParams();
  const { data, loading, error, refetch } = usePublicationDetail(id);
  const { syncing, syncOne } = useCitationSync();
  const [syncMsg, setSyncMsg] = useState(null);

  const handleSync = useCallback(async () => {
    setSyncMsg(null);
    try {
      const r = await syncOne(id);
      setSyncMsg({ ok: true, text: `Synced: ${r.publication?.citations ?? "—"} citations recorded.` });
      setTimeout(() => { refetch(); setSyncMsg(null); }, 1500);
    } catch (e) {
      setSyncMsg({ ok: false, text: e.message });
    }
  }, [id, syncOne, refetch]);

  const handleMarkRead = useCallback(async (alertId) => {
    try {
      await api.patch(`/citations/alerts/${alertId}/read`);
      refetch();
    } catch {}
  }, [refetch]);

  if (loading) return <div className="p-6"><SkeletonCard rows={4} /></div>;

  if (error) {
    return (
      <div className="space-y-6">
        <Link to="/citations"
          className="flex items-center gap-1.5 text-sm text-slate-500 hover:text-[#0F2847] transition-colors">
          <ArrowLeft size={13} /> Back to Citation Tracker
        </Link>
        <div className="border border-slate-200 bg-white p-12 flex flex-col items-center text-center gap-4">
          <AlertCircle size={28} strokeWidth={1} className="text-slate-300" />
          <div>
            <div className="font-serif text-xl text-slate-900">Publication not found</div>
            <div className="text-sm text-slate-500 mt-2">{error}</div>
          </div>
        </div>
      </div>
    );
  }

  const pub        = data?.publication || {};
  const history    = data?.history     || [];
  const sources    = data?.sources     || [];
  const related    = data?.related_pubs || [];
  const alerts     = data?.alerts      || [];
  const impact     = data?.impact_score || {};

  const citations   = pub.citations ?? 0;
  const velocity    = impact.velocity    ?? 0;
  const growthRate  = impact.growth_rate ?? 0;
  const recentDelta = impact.recent_delta ?? 0;

  // chart: reverse history so oldest first, last 20 points
  const chartData = [...history].reverse().slice(-20).map((h, i) => ({
    label:    h.month || `Snap ${i + 1}`,
    citations: h.count,
    delta:     h.delta,
  }));

  // yearly citation chart from counts_by_year
  const yearlyData = (pub.counts_by_year || []).slice(-10);

  return (
    <div data-testid={TID.citationDetailPage(id)} className="space-y-8">
      {/* ─── breadcrumb ──────────────────────────────────────────────────── */}
      <Link to="/citations"
        className="flex items-center gap-1.5 text-sm text-slate-500 hover:text-[#0F2847] transition-colors">
        <ArrowLeft size={13} /> Back to Citation Tracker
      </Link>

      {/* ─── publication header ───────────────────────────────────────────── */}
      <header className="border-b border-slate-200 pb-6">
        <div className="overline text-slate-400 mb-2">Publication</div>
        <h1 className="font-serif text-3xl text-slate-900 leading-snug max-w-3xl">{pub.title}</h1>
        <div className="mt-4 flex flex-wrap items-center gap-4">
          {pub.journal && <span className="text-sm text-slate-600 italic">{pub.journal}</span>}
          {pub.year    && <span className="font-mono text-sm text-slate-500">{pub.year}</span>}
          <span className="text-xs border border-slate-200 text-slate-500 px-1.5 py-0.5 font-mono">
            {(pub.type || "journal_article").replace(/_/g, " ")}
          </span>
          {pub.doi && (
            <a href={`https://doi.org/${pub.doi}`} target="_blank" rel="noopener noreferrer"
              className="flex items-center gap-1 text-xs text-slate-500 hover:text-[#0F2847] transition-colors">
              {pub.doi} <ExternalLink size={10} />
            </a>
          )}
        </div>
        {/* topics / concepts */}
        {((pub.topics || []).length > 0 || (pub.concepts || []).length > 0) && (
          <div className="flex flex-wrap gap-1.5 mt-3">
            {[...(pub.topics || []), ...(pub.concepts || [])].slice(0, 8).map((t) => (
              <span key={t} className="text-xs border border-slate-200 text-slate-500 px-2 py-0.5">{t}</span>
            ))}
          </div>
        )}
        {/* co-authors */}
        {(pub.coauthors || []).length > 0 && (
          <div className="mt-3 flex items-center gap-1.5 flex-wrap">
            <Users size={12} strokeWidth={1.5} className="text-slate-400" />
            {pub.coauthors.slice(0, 5).map((ca, i) => (
              <span key={i} className="text-xs text-slate-500">
                {ca.name}{i < Math.min(4, pub.coauthors.length - 1) ? "," : ""}
              </span>
            ))}
            {pub.coauthors.length > 5 && (
              <span className="text-xs text-slate-400">+{pub.coauthors.length - 5} more</span>
            )}
          </div>
        )}
        <div className="mt-4 flex items-center gap-2">
          <button onClick={handleSync} disabled={syncing}
            className="flex items-center gap-1.5 border border-slate-300 text-slate-600 text-sm px-3 py-1.5 hover:border-[#0F2847] hover:text-[#0F2847] disabled:opacity-50 transition-colors">
            <RefreshCw size={13} className={syncing ? "animate-spin" : ""} />
            {syncing ? "Syncing…" : "Sync This Paper"}
          </button>
          {syncMsg && (
            <span className={`text-sm flex items-center gap-1 ${syncMsg.ok ? "text-green-700" : "text-red-600"}`}>
              {syncMsg.ok ? <CheckCircle2 size={13} /> : <AlertCircle size={13} />}
              {syncMsg.text}
            </span>
          )}
        </div>
      </header>

      {/* ─── hero metrics ─────────────────────────────────────────────────── */}
      <section className="grid sm:grid-cols-2 lg:grid-cols-4 gap-5">
        <div className="border border-[#0F2847] bg-white p-6 text-center">
          <div className="overline mb-2">Total Citations</div>
          <div className="font-serif text-6xl text-[#0F2847] tracking-tight">
            {citations.toLocaleString()}
          </div>
        </div>
        <VelocityGauge velocity={velocity} growthRate={growthRate} recentDelta={recentDelta} />
        <div className="border border-slate-200 bg-white p-5 flex flex-col justify-between">
          <div className="overline mb-2">Research Areas</div>
          <div className="space-y-1.5">
            {((pub.topics || []).concat(pub.concepts || [])).slice(0, 4).map((t) => (
              <div key={t} className="flex items-center gap-1.5">
                <div className="w-1 h-1 rounded-full bg-[#0F2847] shrink-0" />
                <span className="text-sm text-slate-700 truncate">{t}</span>
              </div>
            ))}
            {!((pub.topics || []).concat(pub.concepts || [])).length && (
              <div className="text-sm text-slate-400">No topics yet. Sync to populate.</div>
            )}
          </div>
        </div>
        <div className="border border-slate-200 bg-white p-5">
          <div className="overline mb-2">Alert History</div>
          <div className="font-serif text-4xl text-slate-900 tracking-tight">{alerts.length}</div>
          <div className="text-xs text-slate-400 mt-1">
            {alerts.filter((a) => !a.read).length} unread
          </div>
          <div className="mt-3 space-y-1">
            {Object.entries(
              alerts.reduce((acc, a) => {
                acc[a.alert_type] = (acc[a.alert_type] || 0) + 1;
                return acc;
              }, {})
            ).slice(0, 3).map(([type, count]) => {
              const meta = ALERT_META[type] || { label: type, color: "#64748b" };
              return (
                <div key={type} className="flex items-center justify-between text-xs">
                  <span style={{ color: meta.color }}>{meta.label}</span>
                  <span className="font-mono text-slate-500">{count}</span>
                </div>
              );
            })}
          </div>
        </div>
      </section>

      {/* ─── Feature 8: publication impact breakdown ──────────────────────── */}
      <section>
        <SectionHeader label="Publication Impact Breakdown" icon={Award}
          action={<span className="text-xs text-slate-400 font-mono">40 / 25 / 20 / 15 formula</span>} />
        <div className="border border-slate-200 bg-white p-6">
          <ImpactBreakdown impact={impact} />
        </div>
      </section>

      {/* ─── citation growth chart ────────────────────────────────────────── */}
      {chartData.length > 1 && (
        <section>
          <SectionHeader label="Citation Growth" icon={TrendingUp} />
          <div className="border border-slate-200 bg-white p-6">
            <p className="text-xs text-slate-500 mb-4">
              Citation count across recorded snapshots (newest on the right).
            </p>
            <ResponsiveContainer width="100%" height={200}>
              <AreaChart data={chartData} margin={{ top: 4, right: 4, left: 0, bottom: 4 }}>
                <defs>
                  <linearGradient id="detailGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%"  stopColor="#0F2847" stopOpacity={0.15} />
                    <stop offset="95%" stopColor="#0F2847" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" vertical={false} />
                <XAxis dataKey="label"
                  tick={{ fontSize: 10, fill: "#64748b", fontFamily: "inherit" }}
                  axisLine={false} tickLine={false} />
                <YAxis tick={{ fontSize: 10, fill: "#64748b", fontFamily: "inherit" }}
                  axisLine={false} tickLine={false} width={36} />
                <Tooltip content={<ChartTooltip />} cursor={{ fill: "#f8fafc" }} />
                <Area type="monotone" dataKey="citations" name="Citations"
                  stroke="#0F2847" strokeWidth={2} fill="url(#detailGrad)" />
              </AreaChart>
            </ResponsiveContainer>

            {/* snapshot table */}
            <div className="mt-5 overflow-x-auto">
              <table className="w-full text-sm border-collapse">
                <thead>
                  <tr className="border-b border-slate-200">
                    <th className="text-left py-2 overline font-normal text-slate-500">Date</th>
                    <th className="text-right py-2 overline font-normal text-slate-500">Month</th>
                    <th className="text-right py-2 overline font-normal text-slate-500">Citations</th>
                    <th className="text-right py-2 overline font-normal text-slate-500">Change</th>
                  </tr>
                </thead>
                <tbody>
                  {history.slice(0, 20).map((h, i) => (
                    <tr key={i} className="border-b border-slate-100 hover:bg-slate-50">
                      <td className="py-2.5 text-slate-600 text-xs">
                        {new Date(h.date).toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric" })}
                      </td>
                      <td className="py-2.5 text-right font-mono text-slate-500 text-xs">{h.month || "—"}</td>
                      <td className="py-2.5 text-right font-medium text-slate-900">{h.count.toLocaleString()}</td>
                      <td className="py-2.5 text-right">
                        {h.delta > 0
                          ? <span className="text-green-600 font-mono text-xs">+{h.delta}</span>
                          : <span className="text-slate-300 font-mono text-xs">—</span>}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </section>
      )}

      {/* ─── yearly citation chart from OpenAlex counts_by_year ──────────── */}
      {yearlyData.length > 1 && (
        <section>
          <SectionHeader label="Citation Rate by Year" icon={BarChart} />
          <div className="border border-slate-200 bg-white p-6">
            <p className="text-xs text-slate-500 mb-4">
              Citations received each year as reported by OpenAlex.
            </p>
            <ResponsiveContainer width="100%" height={180}>
              <BarChart data={yearlyData} margin={{ top: 4, right: 4, left: 0, bottom: 4 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" vertical={false} />
                <XAxis dataKey="year"
                  tick={{ fontSize: 10, fill: "#64748b", fontFamily: "inherit" }}
                  axisLine={false} tickLine={false} />
                <YAxis tick={{ fontSize: 10, fill: "#64748b", fontFamily: "inherit" }}
                  axisLine={false} tickLine={false} width={30} />
                <Tooltip content={<ChartTooltip />} cursor={{ fill: "#f8fafc" }} />
                <Bar dataKey="count" name="Citations" fill="#0F2847" radius={[2, 2, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </section>
      )}

      {/* ─── citation sources ─────────────────────────────────────────────── */}
      <section>
        <SectionHeader label="Citation Sources" icon={BookOpen}
          action={<span className="text-xs text-slate-400 font-mono">{sources.length} citing papers</span>} />
        {sources.length > 0 ? (
          <div className="border border-slate-200 bg-white overflow-x-auto">
            <table className="w-full text-sm border-collapse">
              <thead>
                <tr className="border-b border-slate-200 bg-slate-50">
                  <th className="text-left px-4 py-3 overline font-normal text-slate-500">Citing Paper</th>
                  <th className="text-right px-4 py-3 overline font-normal text-slate-500 whitespace-nowrap">Year</th>
                  <th className="px-4 py-3 overline font-normal text-slate-500 whitespace-nowrap">Journal</th>
                  <th className="px-4 py-3 overline font-normal text-slate-500 whitespace-nowrap">DOI</th>
                </tr>
              </thead>
              <tbody>
                {sources.map((s) => (
                  <tr key={s.id} className="border-b border-slate-100 hover:bg-slate-50">
                    <td className="px-4 py-3 text-slate-800 max-w-xs">
                      <div className="line-clamp-2">{s.title || "—"}</div>
                    </td>
                    <td className="px-4 py-3 text-right font-mono text-slate-600">{s.year || "—"}</td>
                    <td className="px-4 py-3 text-slate-500 text-xs max-w-xs">
                      <div className="truncate">{s.journal || "—"}</div>
                    </td>
                    <td className="px-4 py-3">
                      {s.doi ? (
                        <a href={`https://doi.org/${s.doi}`} target="_blank" rel="noopener noreferrer"
                          className="flex items-center gap-0.5 text-xs text-slate-500 hover:text-[#0F2847] transition-colors">
                          {s.doi.substring(0, 18)}{s.doi.length > 18 ? "…" : ""}
                          <ExternalLink size={10} />
                        </a>
                      ) : <span className="text-xs text-slate-300">—</span>}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="border border-slate-200 bg-white p-8 text-center">
            <div className="text-slate-400 text-sm">No citation sources recorded yet.</div>
            <div className="text-xs text-slate-400 mt-1">
              Sources are populated from OpenAlex when you sync this paper.
            </div>
            <button onClick={handleSync} disabled={syncing}
              className="mt-3 flex items-center gap-1.5 mx-auto border border-slate-300 text-slate-600 text-sm px-4 py-2 hover:border-[#0F2847] hover:text-[#0F2847] disabled:opacity-50 transition-colors">
              <RefreshCw size={12} className={syncing ? "animate-spin" : ""} />
              {syncing ? "Syncing…" : "Sync This Paper"}
            </button>
          </div>
        )}
      </section>

      {/* ─── related publications ─────────────────────────────────────────── */}
      {related.length > 0 && (
        <section>
          <SectionHeader label="Related Publications" icon={GitBranch}
            action={<span className="text-xs text-slate-400 font-mono">same research areas</span>} />
          <div className="grid sm:grid-cols-2 gap-4">
            {related.map((r) => (
              <Link key={r.id} to={`/citations/${r.id}`}
                className="border border-slate-200 bg-white p-4 hover:border-[#0F2847] transition-colors group">
                <div className="font-medium text-slate-900 text-sm line-clamp-2 group-hover:text-[#0F2847] transition-colors">
                  {r.title}
                </div>
                <div className="flex items-center gap-3 mt-2 text-xs text-slate-500">
                  <span className="font-mono">{r.citations.toLocaleString()} cit.</span>
                  {r.year && <span>{r.year}</span>}
                </div>
                {(r.topics || []).length > 0 && (
                  <div className="flex flex-wrap gap-1 mt-2">
                    {r.topics.slice(0, 3).map((t) => (
                      <span key={t} className="text-xs border border-slate-100 text-slate-400 px-1.5 py-0.5">{t}</span>
                    ))}
                  </div>
                )}
                <div className="flex items-center gap-0.5 text-xs text-slate-300 group-hover:text-[#0F2847] mt-2 transition-colors">
                  View detail <ChevronRight size={10} />
                </div>
              </Link>
            ))}
          </div>
        </section>
      )}

      {/* ─── alert history ────────────────────────────────────────────────── */}
      <section>
        <SectionHeader label="Alert History" icon={Bell}
          action={<span className="text-xs text-slate-400 font-mono">{alerts.filter((a) => !a.read).length} unread</span>} />
        {alerts.length > 0 ? (
          <div className="border border-slate-200 bg-white p-5">
            {alerts.map((a) => (
              <div key={a.id}
                className={`flex items-start gap-3 py-3 border-b border-slate-100 last:border-0 ${a.read ? "opacity-55" : ""}`}>
                <div className="w-1.5 h-1.5 rounded-full mt-2 shrink-0"
                  style={{ background: (ALERT_META[a.alert_type] || {}).color || "#64748b" }} />
                <div className="flex-1 min-w-0">
                  <div className="text-sm text-slate-800">{a.message}</div>
                  <div className="flex items-center gap-2 mt-0.5">
                    <AlertBadge type={a.alert_type} />
                    <span className="text-xs text-slate-400">
                      {new Date(a.created_at).toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric" })}
                    </span>
                  </div>
                </div>
                {!a.read && (
                  <button onClick={() => handleMarkRead(a.id)}
                    className="shrink-0 text-slate-300 hover:text-slate-600 transition-colors" title="Mark as read">
                    <CheckCircle2 size={14} />
                  </button>
                )}
              </div>
            ))}
          </div>
        ) : (
          <div className="border border-slate-200 bg-white p-8 text-center text-sm text-slate-400">
            No alerts for this publication yet.
          </div>
        )}
      </section>

      <DataNote>
        Citation history is built from point-in-time snapshots. Use "Sync This Paper" to update
        via OpenAlex. Sources are populated from citing-works API calls on each sync.{" "}
        <Link to="/citations" className="underline hover:text-amber-900">Citation Tracker</Link>
      </DataNote>
    </div>
  );
}
