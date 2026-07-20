import React, { useState, useCallback } from "react";
import { Link } from "react-router-dom";
import { ResearchLayout } from "@/layouts";
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
} from "recharts";
import {
  Lock, Download, TrendingUp, Award, BookOpen, Zap, RefreshCw, ExternalLink,
  CheckCircle2, XCircle, ChevronRight, Bell, BellOff, BarChart2, Target,
  Sparkles, ArrowUpRight, Info, Upload, GitBranch, AlertCircle,
} from "lucide-react";
import api from "../lib/api";
import { TID } from "../lib/testIds";
import { NAVY, WARM } from "@/lib/tokens";
import { Spinner } from "@/components/ds/LoadingState";
import {
  useCitationDashboard,
  useResearchAreas,
  useCitationSync,
} from "../hooks/useCitations";

// ─────────────────────────── research intelligence nav ───────────────────────

const INTEL_NAV = [
  { to: "/analytics",           label: "Analytics"    },
  { to: "/research-impact",     label: "Impact"       },
  { to: "/impact-dashboard",    label: "Dashboard"    },
  { to: "/citations",           label: "Citations"    },
  { to: "/citation-monitoring", label: "Monitoring"   },
  { to: "/reputation",          label: "Reputation"   },
  { to: "/verification",        label: "Verification" },
];

function IntelNav({ current }) {
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 2, flexWrap: "wrap" }}>
      {INTEL_NAV.map((s, i) => {
        const isCur = s.to === current;
        return (
          <React.Fragment key={s.to}>
            {i > 0 && <ChevronRight size={10} strokeWidth={1.5} style={{ color: "#CBD5E1", flexShrink: 0 }} />}
            <Link to={s.to} style={{ fontSize: 11, fontWeight: isCur ? 700 : 400, color: isCur ? "#0F2847" : "#94A3B8", padding: "3px 7px", background: isCur ? "rgba(15,40,71,0.07)" : "transparent", borderRadius: 3, textDecoration: "none", whiteSpace: "nowrap" }}>
              {s.label}
            </Link>
          </React.Fragment>
        );
      })}
    </div>
  );
}

// ─────────────────────────── primitives ──────────────────────────────────────

function Stat({ label, value, sub, highlight }) {
  return (
    <div className={`border bg-white p-6 ${highlight ? "border-[#0F2847]" : "border-slate-200"}`}>
      <div className="overline">{label}</div>
      <div className={`font-serif text-5xl mt-3 tracking-tight ${highlight ? "text-[#0F2847]" : "text-slate-900"}`}>
        {value}
      </div>
      {sub && <div className="text-xs text-slate-500 mt-2">{sub}</div>}
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

function DataNote({ children }) {
  return (
    <div className="flex items-start gap-2 border border-amber-100 bg-amber-50 p-3 text-xs text-amber-800">
      <Info size={12} className="shrink-0 mt-0.5 text-amber-600" />
      <span>{children}</span>
    </div>
  );
}

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

// ─────────────────────────── gate view ───────────────────────────────────────

function GateView() {
  return (
    <div className="space-y-6">
      <header className="border-b border-slate-200 pb-6">
        <div className="overline">Research Impact</div>
        <h1 className="font-serif text-5xl text-slate-900 mt-2">Citation Tracker</h1>
      </header>
      <div className="border border-slate-200 bg-white p-16 flex flex-col items-center text-center gap-5">
        <Lock size={28} strokeWidth={1} className="text-slate-300" />
        <div>
          <div className="overline text-[#0F2847] mb-2">Pro Researcher plan required</div>
          <h2 className="font-serif text-2xl text-slate-900">Citation Tracking is a Pro feature</h2>
          <p className="text-slate-500 text-sm mt-3 max-w-sm mx-auto">
            Track citation growth, monitor milestones, receive alerts for new citations,
            and analyse your publication impact over time.
          </p>
        </div>
        <Link to="/pricing"
          className="inline-block bg-[#0F2847] text-white text-sm px-6 py-2.5 hover:opacity-90 transition-opacity">
          View Plans
        </Link>
      </div>
    </div>
  );
}

// ─────────────────────────── no-data prompt ──────────────────────────────────

function NoDataPrompt({ onSync, onImport, syncing }) {
  return (
    <div className="border border-slate-200 bg-white p-12 flex flex-col items-center text-center gap-5">
      <BookOpen size={32} strokeWidth={1} className="text-slate-300" />
      <div>
        <h2 className="font-serif text-xl text-slate-900">No citation data yet</h2>
        <p className="text-slate-500 text-sm mt-2 max-w-md mx-auto">
          Import your publications from ORCID, then sync with OpenAlex to populate
          your citation dashboard. Make sure your ORCID is linked in your Academic Passport.
        </p>
      </div>
      <div className="flex flex-wrap gap-3 justify-center">
        <button onClick={onImport} disabled={syncing}
          className="flex items-center gap-2 bg-[#0F2847] text-white text-sm px-5 py-2 hover:opacity-90 disabled:opacity-50 transition-opacity">
          <Upload size={13} />
          {syncing ? "Importing…" : "Import from ORCID"}
        </button>
        <button onClick={onSync} disabled={syncing}
          className="flex items-center gap-2 border border-slate-300 text-slate-600 text-sm px-5 py-2 hover:border-[#0F2847] hover:text-[#0F2847] disabled:opacity-50 transition-colors">
          <RefreshCw size={13} className={syncing ? "animate-spin" : ""} />
          {syncing ? "Syncing…" : "Sync OpenAlex"}
        </button>
        <Link to="/academic-passport"
          className="flex items-center gap-2 border border-slate-200 text-slate-500 text-sm px-5 py-2 hover:border-slate-400 transition-colors">
          ORCID Settings
        </Link>
      </div>
    </div>
  );
}

// ─────────────────────────── alert row ───────────────────────────────────────

const ALERT_META = {
  new_citation:  { label: "New Citation",    color: "#2563eb" },
  milestone:     { label: "Milestone",       color: "#16a34a" },
  highly_cited:  { label: "Highly Cited",    color: "#7c3aed" },
  velocity:      { label: "High Velocity",   color: "#d97706" },
  rapid_growth:  { label: "Rapid Growth",    color: "#dc2626" },
  emerging_topic:{ label: "Emerging",        color: "#0891b2" },
  top_performer: { label: "Top Performer",   color: "#16a34a" },
  high_velocity: { label: "High Velocity",   color: "#d97706" },
};

function AlertRow({ alert, onRead }) {
  const meta = ALERT_META[alert.alert_type] || { label: alert.alert_type, color: "#64748b" };
  return (
    <div className={`flex items-start gap-3 py-3 border-b border-slate-100 last:border-0 ${alert.read ? "opacity-55" : ""}`}>
      <div className="w-1.5 h-1.5 rounded-full mt-2 shrink-0" style={{ background: meta.color }} />
      <div className="flex-1 min-w-0">
        <div className="text-sm text-slate-800">{alert.message}</div>
        <div className="flex items-center gap-2 mt-0.5">
          <span className="text-xs font-mono" style={{ color: meta.color }}>{meta.label}</span>
          <span className="text-xs text-slate-400">
            {new Date(alert.created_at).toLocaleDateString("en-GB", { day: "numeric", month: "short" })}
          </span>
        </div>
      </div>
      {!alert.read && (
        <button onClick={() => onRead(alert.id)}
          className="shrink-0 text-slate-300 hover:text-slate-600 transition-colors" title="Mark as read">
          <CheckCircle2 size={14} />
        </button>
      )}
    </div>
  );
}

// ─────────────────────────── research area card ───────────────────────────────

const TREND_META = {
  rising:   { label: "Rising",    color: "#16a34a" },
  growing:  { label: "Growing",   color: "#2563eb" },
  emerging: { label: "Emerging",  color: "#0891b2" },
  stable:   { label: "Stable",    color: "#64748b" },
  declining:{ label: "Declining", color: "#dc2626" },
};

function AreaCard({ area, rank }) {
  const trend = TREND_META[area.trend] || { label: area.trend, color: "#64748b" };
  const pct = area.growth_rate > 0 ? `+${area.growth_rate}%` : area.growth_rate < 0 ? `${area.growth_rate}%` : "0%";
  return (
    <div className="border border-slate-200 bg-white p-5">
      <div className="flex items-start justify-between gap-2 mb-3">
        <div className="flex items-center gap-2 min-w-0">
          {rank && <span className="font-mono text-slate-300 text-xs shrink-0">{rank}</span>}
          <div className="font-medium text-slate-900 text-sm truncate">{area.area}</div>
        </div>
        <span className="text-xs border px-1.5 py-0.5 font-mono shrink-0"
          style={{ borderColor: trend.color, color: trend.color }}>{trend.label}</span>
      </div>
      <div className="grid grid-cols-3 gap-3 text-center">
        <div>
          <div className="font-serif text-xl text-slate-900">{area.total_citations.toLocaleString()}</div>
          <div className="text-xs text-slate-400 mt-0.5">citations</div>
        </div>
        <div>
          <div className="font-serif text-xl text-slate-900">{area.avg_citations}</div>
          <div className="text-xs text-slate-400 mt-0.5">avg</div>
        </div>
        <div>
          <div className={`font-serif text-xl ${area.growth_rate > 0 ? "text-green-600" : area.growth_rate < 0 ? "text-red-500" : "text-slate-900"}`}>
            {pct}
          </div>
          <div className="text-xs text-slate-400 mt-0.5">growth</div>
        </div>
      </div>
      <div className="mt-3">
        <div className="flex justify-between text-xs mb-1">
          <span className="text-slate-400">{area.publication_count} pub{area.publication_count !== 1 ? "s" : ""}</span>
          <span className="font-mono text-slate-500">score {area.impact_score}</span>
        </div>
        <div className="h-1 bg-slate-100 relative">
          <div className="absolute inset-y-0 left-0 bg-[#0F2847]" style={{ width: `${Math.min(100, area.impact_score)}%` }} />
        </div>
      </div>
    </div>
  );
}

// ─────────────────────────── transparent score ────────────────────────────────

function TransparentScore({ impact }) {
  if (!impact) return null;
  const components = Object.values(impact.components || {});
  return (
    <div className="border border-slate-200 bg-white p-6">
      <div className="flex items-center gap-4 mb-6">
        <div className="text-center">
          <div className="font-serif text-6xl text-[#0F2847] tracking-tight">{impact.score}</div>
          <div className="text-xs text-slate-400 mt-1">/ 100</div>
        </div>
        <div className="flex-1 min-w-0">
          <div className="font-medium text-slate-900 text-sm">Research Impact Score</div>
          <div className="text-xs text-slate-500 mt-1 font-mono">{impact.formula}</div>
        </div>
      </div>
      <div className="space-y-4">
        {components.map((c) => (
          <div key={c.label}>
            <div className="flex items-center justify-between mb-1">
              <div className="flex items-center gap-2">
                <span className="text-sm font-medium text-slate-700">{c.label}</span>
                <span className="text-xs text-slate-400 font-mono">
                  {Math.round(c.weight * 100)}% weight · {c.contribution} pts
                </span>
              </div>
              <span className="font-serif text-lg text-slate-900">{c.value}</span>
            </div>
            <div className="h-2 bg-slate-100 relative mb-1.5">
              <div className="absolute inset-y-0 left-0 bg-[#0F2847] transition-all"
                style={{ width: `${Math.min(100, c.value)}%`, opacity: c.weight + 0.3 }} />
            </div>
            <div className="text-xs text-slate-400 leading-relaxed">{c.reasoning}</div>
          </div>
        ))}
      </div>
    </div>
  );
}

// ─────────────────────────── pub row ─────────────────────────────────────────

function PubRow({ pub }) {
  return (
    <tr className="border-b border-slate-100 hover:bg-slate-50 transition-colors">
      <td className="px-4 py-3 text-slate-800 max-w-xs">
        <Link to={`/citations/${pub.id}`}
          className="line-clamp-2 hover:text-[#0F2847] hover:underline transition-colors"
          data-testid={TID.citationPubRow(pub.id)}>
          {pub.title}
        </Link>
        {pub.journal && <div className="text-xs text-slate-400 mt-0.5 truncate">{pub.journal}</div>}
        {(pub.topics || pub.concepts || []).length > 0 && (
          <div className="flex flex-wrap gap-1 mt-1">
            {(pub.topics || pub.concepts || []).slice(0, 2).map((t) => (
              <span key={t} className="text-xs border border-slate-100 text-slate-400 px-1.5 py-0.5">{t}</span>
            ))}
          </div>
        )}
      </td>
      <td className="px-4 py-3 text-right font-mono text-slate-600 whitespace-nowrap">{pub.year || "—"}</td>
      <td className="px-4 py-3 text-right whitespace-nowrap">
        <span className={`font-serif text-lg ${pub.citations > 0 ? "text-slate-900" : "text-slate-300"}`}>
          {pub.citations.toLocaleString()}
        </span>
      </td>
      <td className="px-4 py-3 text-right whitespace-nowrap">
        <span className="text-xs border border-slate-200 text-slate-500 px-1.5 py-0.5 font-mono">
          {(pub.type || "article").replace(/_/g, " ")}
        </span>
      </td>
      <td className="px-4 py-3 whitespace-nowrap">
        {pub.doi ? (
          <a href={`https://doi.org/${pub.doi}`} target="_blank" rel="noopener noreferrer"
            className="flex items-center gap-0.5 text-xs text-slate-500 hover:text-[#0F2847] transition-colors">
            {pub.doi.substring(0, 18)}{pub.doi.length > 18 ? "…" : ""}<ExternalLink size={10} />
          </a>
        ) : <span className="text-xs text-slate-300">—</span>}
      </td>
      <td className="px-4 py-3 text-right">
        <Link to={`/citations/${pub.id}`}
          className="flex items-center justify-end gap-0.5 text-xs text-slate-400 hover:text-[#0F2847] transition-colors">
          View <ChevronRight size={11} />
        </Link>
      </td>
    </tr>
  );
}

// ─────────────────────────── main page ───────────────────────────────────────

export default function Citations() {
  const { data, loading, error, refetch } = useCitationDashboard();
  const { data: areasData, loading: areasLoading, refetch: refetchAreas } = useResearchAreas();
  const { syncing, syncAll, importOrcid } = useCitationSync();

  const [gated, setGated]       = useState(false);
  const [syncMsg, setSyncMsg]   = useState(null);
  const [alertTab, setAlertTab] = useState("all");
  const [exporting, setExporting] = useState(false);

  // detect 402 from dashboard hook
  const isGated = error && error.includes && error.includes("402");

  const handleSync = useCallback(async () => {
    setSyncMsg(null);
    try {
      await syncAll();
      setSyncMsg({ ok: true, text: "Sync complete. Refreshing data…" });
      setTimeout(() => { refetch(); refetchAreas(); setSyncMsg(null); }, 1500);
    } catch (e) {
      setSyncMsg({ ok: false, text: e.message });
    }
  }, [syncAll, refetch, refetchAreas]);

  const handleImport = useCallback(async () => {
    setSyncMsg(null);
    try {
      const r = await importOrcid();
      setSyncMsg({ ok: true, text: `Imported ${r.imported} publication${r.imported !== 1 ? "s" : ""} from ORCID. Refreshing…` });
      setTimeout(() => { refetch(); refetchAreas(); setSyncMsg(null); }, 1500);
    } catch (e) {
      setSyncMsg({ ok: false, text: e.message });
    }
  }, [importOrcid, refetch, refetchAreas]);

  const handleMarkRead = useCallback(async (alertId) => {
    try {
      await api.patch(`/citations/alerts/${alertId}/read`);
      refetch();
    } catch {}
  }, [refetch]);

  const handleMarkAllRead = useCallback(async () => {
    try {
      await api.patch("/citations/alerts/read-all");
      refetch();
    } catch {}
  }, [refetch]);

  const handleExport = async () => {
    setExporting(true);
    try {
      const resp = await api.get("/citations/export", { responseType: "blob" });
      const url  = URL.createObjectURL(resp.data);
      const a    = document.createElement("a");
      a.href     = url;
      a.download = `citations_${new Date().toISOString().slice(0, 10)}.csv`;
      a.click();
      URL.revokeObjectURL(url);
    } catch {}
    setExporting(false);
  };

  if (loading) return <div className="py-12 flex justify-center"><Spinner size={20} /></div>;

  // check if gated via api error
  if (isGated) return <GateView />;

  const summary   = data?.summary   || {};
  const pubs      = data?.publications || [];
  const timeline  = data?.timeline   || [];
  const alerts    = data?.alerts     || [];
  const insights  = data?.impact_insights || {};
  const impact    = data?.impact_score || {};
  const author    = data?.author     || {};
  const mostCited = data?.most_cited_pub;
  const hasData   = summary.has_data || pubs.length > 0;

  const areas      = areasData?.areas      || [];
  const classified = areasData?.classified || {};

  const filteredAlerts = alertTab === "unread" ? alerts.filter((a) => !a.read) : alerts;

  const citationsActions = (
    <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
      <button onClick={handleImport} disabled={syncing} data-testid={TID.citationsImportBtn}
        style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 12, color: "#64748B", padding: "8px 14px", border: "1px solid rgba(15,23,42,0.08)", background: "#fff", cursor: "pointer", opacity: syncing ? 0.5 : 1 }}>
        <Upload size={12} strokeWidth={1.5} />{syncing ? "Working…" : "Import ORCID"}
      </button>
      <button onClick={handleSync} disabled={syncing} data-testid={TID.citationsSyncBtn}
        style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 12, color: "#64748B", padding: "8px 14px", border: "1px solid rgba(15,23,42,0.08)", background: "#fff", cursor: "pointer", opacity: syncing ? 0.5 : 1 }}>
        <RefreshCw size={12} strokeWidth={1.5} className={syncing ? "animate-spin" : ""} />{syncing ? "Syncing…" : "Sync & Track"}
      </button>
      <button onClick={handleExport} disabled={exporting || !hasData} data-testid={TID.citationsExportBtn}
        style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 12, color: "#fff", padding: "8px 14px", background: "#0F2847", border: "none", cursor: "pointer", opacity: (exporting || !hasData) ? 0.5 : 1 }}>
        <Download size={12} strokeWidth={1.5} />{exporting ? "Exporting…" : "Export CSV"}
      </button>
    </div>
  );

  return (
    <ResearchLayout
      title="Citations"
      subtitle="Track citation impact, monitor new citations, and export your research influence data."
      nav={<IntelNav current="/citations" />}
      actions={citationsActions}
    >
      <div data-testid={TID.citationsDashboard} className="space-y-10">
      {syncMsg && (
        <div style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 12, color: syncMsg.ok ? "#047857" : "#DC2626" }}>
          {syncMsg.ok ? <CheckCircle2 size={13} /> : <XCircle size={13} />}
          {syncMsg.text}
        </div>
      )}

      {!hasData ? (
        <NoDataPrompt onSync={handleSync} onImport={handleImport} syncing={syncing} />
      ) : (
        <>
          {/* ─── citation tracker stats ───────────────────────────────────── */}
          <section>
            <SectionHeader label="Citation Tracker" icon={BarChart2} />
            <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-5">
              <Stat label="Total Citations"
                value={summary.total_citations?.toLocaleString() ?? 0}
                sub={`h-index: ${summary.h_index} · i10: ${summary.i10_index}`} />
              <Stat label="New Citations"
                value={`+${summary.new_citations ?? 0}`}
                sub="Since last snapshot"
                highlight={(summary.new_citations ?? 0) > 0} />
              <Stat label="Citations This Month"
                value={`+${summary.this_month ?? 0}`}
                sub={new Date().toLocaleString("en-GB", { month: "long", year: "numeric" })} />
              <Stat label="Most Cited Paper"
                value={mostCited ? mostCited.citations.toLocaleString() : "—"}
                sub={mostCited ? mostCited.title.slice(0, 40) + (mostCited.title.length > 40 ? "…" : "") : "No data yet"} />
            </div>
          </section>

          {/* ─── citation timeline ────────────────────────────────────────── */}
          {timeline.length > 0 && (
            <section>
              <SectionHeader label="Citation Timeline" icon={TrendingUp}
                action={<span className="text-xs text-slate-400 font-mono">{pubs.length} publications · by year</span>} />
              <div className="border border-slate-200 bg-white p-6">
                <ResponsiveContainer width="100%" height={220}>
                  <AreaChart data={timeline} margin={{ top: 4, right: 4, left: 0, bottom: 4 }}>
                    <defs>
                      <linearGradient id="citGrad" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%"  stopColor="#0F2847" stopOpacity={0.15} />
                        <stop offset="95%" stopColor="#0F2847" stopOpacity={0} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" vertical={false} />
                    <XAxis dataKey="year"
                      tick={{ fontSize: 11, fill: "#64748b", fontFamily: "inherit" }}
                      axisLine={false} tickLine={false} />
                    <YAxis tick={{ fontSize: 11, fill: "#64748b", fontFamily: "inherit" }}
                      axisLine={false} tickLine={false} width={40} />
                    <Tooltip content={<ChartTooltip />} cursor={{ fill: "#f8fafc" }} />
                    <Area type="monotone" dataKey="total_citations" name="Total Citations"
                      stroke="#0F2847" strokeWidth={2} fill="url(#citGrad)" />
                  </AreaChart>
                </ResponsiveContainer>
                <div className="mt-5 overflow-x-auto">
                  <table className="w-full text-sm border-collapse">
                    <thead>
                      <tr className="border-b border-slate-200">
                        <th className="text-left py-2 overline font-normal text-slate-500">Year</th>
                        <th className="text-right py-2 overline font-normal text-slate-500">Publications</th>
                        <th className="text-right py-2 overline font-normal text-slate-500">Total Citations</th>
                        <th className="text-right py-2 overline font-normal text-slate-500">Avg / Paper</th>
                      </tr>
                    </thead>
                    <tbody>
                      {[...timeline].reverse().map((row) => (
                        <tr key={row.year} className="border-b border-slate-100 hover:bg-slate-50">
                          <td className="py-2.5 font-mono text-slate-900">{row.year}</td>
                          <td className="py-2.5 text-right text-slate-700">{row.publications}</td>
                          <td className="py-2.5 text-right font-medium text-slate-900">{row.total_citations.toLocaleString()}</td>
                          <td className="py-2.5 text-right text-slate-600">{row.avg_citations}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </section>
          )}

          {/* ─── Feature 3: research area impact ──────────────────────────── */}
          <section>
            <SectionHeader label="Research Area Impact" icon={GitBranch}
              action={areasLoading ? (
                <RefreshCw size={12} className="animate-spin text-slate-400" />
              ) : null} />
            {areas.length === 0 && !areasLoading ? (
              <div className="border border-slate-200 bg-white p-8 text-center text-sm text-slate-400">
                No research area data yet. Sync publications with OpenAlex to populate topics and concepts.
              </div>
            ) : (
              <div className="space-y-6">
                {/* top areas */}
                {(classified.top_areas || []).length > 0 && (
                  <div>
                    <div className="text-xs text-slate-500 font-mono mb-3 flex items-center gap-1.5">
                      <Award size={11} className="text-[#16a34a]" />
                      Top Research Areas
                    </div>
                    <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
                      {(classified.top_areas || []).map((a, i) => (
                        <AreaCard key={a.area} area={a} rank={`#${i + 1}`} />
                      ))}
                    </div>
                  </div>
                )}

                {/* fastest growing + emerging grid */}
                <div className="grid lg:grid-cols-2 gap-5">
                  {(classified.fastest_growing || []).length > 0 && (
                    <div className="border border-slate-200 bg-white p-5">
                      <div className="flex items-center gap-2 mb-4">
                        <TrendingUp size={13} strokeWidth={1.5} className="text-[#d97706]" />
                        <div className="overline text-[#d97706]">Fastest Growing Topics</div>
                      </div>
                      <div className="space-y-3">
                        {(classified.fastest_growing || []).map((a) => (
                          <div key={a.area} className="flex items-center justify-between gap-3">
                            <div className="flex-1 min-w-0">
                              <div className="text-sm text-slate-800 truncate">{a.area}</div>
                              <div className="text-xs text-slate-500 mt-0.5">{a.total_citations.toLocaleString()} citations</div>
                            </div>
                            <span className="text-sm font-mono text-green-600 shrink-0">+{a.growth_rate}%</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {(classified.emerging || []).length > 0 && (
                    <div className="border border-slate-200 bg-white p-5">
                      <div className="flex items-center gap-2 mb-4">
                        <Zap size={13} strokeWidth={1.5} className="text-[#0891b2]" />
                        <div className="overline text-[#0891b2]">Emerging Topics</div>
                      </div>
                      <div className="space-y-3">
                        {(classified.emerging || []).map((a) => (
                          <div key={a.area} className="flex items-center justify-between gap-3">
                            <div className="flex-1 min-w-0">
                              <div className="text-sm text-slate-800 truncate">{a.area}</div>
                              <div className="text-xs text-slate-500 mt-0.5">{a.publication_count} pub{a.publication_count !== 1 ? "s" : ""}</div>
                            </div>
                            <span className="text-xs border border-[#0891b2] text-[#0891b2] px-1.5 py-0.5 font-mono">Emerging</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>

                {/* declining topics */}
                {(classified.declining || []).length > 0 && (
                  <div className="border border-amber-100 bg-amber-50 p-4">
                    <div className="flex items-center gap-2 mb-3">
                      <AlertCircle size={13} className="text-amber-600" />
                      <div className="overline text-amber-700">Declining Topics</div>
                    </div>
                    <div className="flex flex-wrap gap-3">
                      {(classified.declining || []).map((a) => (
                        <div key={a.area} className="text-xs text-amber-800">
                          {a.area} <span className="font-mono text-amber-600">({a.growth_rate}%)</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}
          </section>

          {/* ─── publications table ───────────────────────────────────────── */}
          {pubs.length > 0 && (
            <section>
              <SectionHeader label="Publications" icon={BookOpen}
                action={
                  <Link to="/citation-monitoring"
                    className="text-xs text-slate-400 hover:text-[#0F2847] font-mono flex items-center gap-1 transition-colors">
                    Full dashboard <ArrowUpRight size={10} />
                  </Link>
                } />
              <div className="border border-slate-200 bg-white overflow-x-auto">
                <table className="w-full text-sm border-collapse">
                  <thead>
                    <tr className="border-b border-slate-200 bg-slate-50">
                      <th className="text-left px-4 py-3 overline font-normal text-slate-500">Title</th>
                      <th className="text-right px-4 py-3 overline font-normal text-slate-500 whitespace-nowrap">Year</th>
                      <th className="text-right px-4 py-3 overline font-normal text-slate-500 whitespace-nowrap">Citations</th>
                      <th className="text-right px-4 py-3 overline font-normal text-slate-500 whitespace-nowrap">Type</th>
                      <th className="px-4 py-3 overline font-normal text-slate-500 whitespace-nowrap">DOI</th>
                      <th className="px-4 py-3" />
                    </tr>
                  </thead>
                  <tbody>{pubs.map((pub) => <PubRow key={pub.id} pub={pub} />)}</tbody>
                </table>
              </div>
            </section>
          )}

          {/* ─── citation alerts ──────────────────────────────────────────── */}
          <section>
            <SectionHeader label="Citation Alerts" icon={Bell}
              action={
                <div className="flex items-center gap-3">
                  {summary.unread_alerts > 0 && (
                    <button onClick={handleMarkAllRead}
                      className="text-xs text-slate-400 hover:text-[#0F2847] flex items-center gap-1 transition-colors">
                      <BellOff size={11} /> Mark all read
                    </button>
                  )}
                  <div className="flex border border-slate-200 text-xs">
                    {["all", "unread"].map((t) => (
                      <button key={t} onClick={() => setAlertTab(t)}
                        className={`px-3 py-1 capitalize transition-colors ${alertTab === t ? "bg-[#0F2847] text-white" : "text-slate-500 hover:text-slate-900"}`}>
                        {t}{t === "unread" && summary.unread_alerts > 0 && (
                          <span className="ml-1 font-mono">{summary.unread_alerts}</span>
                        )}
                      </button>
                    ))}
                  </div>
                </div>
              } />
            <div className="border border-slate-200 bg-white p-5">
              {filteredAlerts.length === 0 ? (
                <div className="py-8 text-center text-slate-400 text-sm">
                  {alertTab === "unread" ? "No unread alerts." : "No alerts yet. Sync to detect new citations."}
                </div>
              ) : (
                filteredAlerts.map((a) => <AlertRow key={a.id} alert={a} onRead={handleMarkRead} />)
              )}
            </div>
          </section>

          {/* ─── impact insights ──────────────────────────────────────────── */}
          <section>
            <SectionHeader label="Impact Insights" icon={Sparkles} />
            <div className="grid lg:grid-cols-3 gap-5">
              <div className="border border-slate-200 bg-white p-5">
                <div className="flex items-center gap-2 mb-4">
                  <Award size={13} strokeWidth={1.5} className="text-[#16a34a]" />
                  <div className="overline text-[#16a34a]">Top Performing</div>
                </div>
                {(insights.top_performing || []).slice(0, 5).map((p, i) => (
                  <div key={p.id} className="flex items-start gap-3 mb-3 last:mb-0">
                    <span className="font-mono text-slate-300 text-xs mt-0.5 w-4 shrink-0">{i + 1}</span>
                    <div className="flex-1 min-w-0">
                      <Link to={`/citations/${p.id}`}
                        className="text-sm text-slate-800 line-clamp-2 hover:text-[#0F2847] transition-colors">{p.title}</Link>
                      <div className="text-xs text-slate-500 mt-0.5 font-mono">
                        {p.citations.toLocaleString()} cit{p.year ? ` · ${p.year}` : ""}
                      </div>
                    </div>
                  </div>
                ))}
                {!(insights.top_performing || []).length && <div className="text-sm text-slate-400">No data yet.</div>}
              </div>

              <div className="border border-slate-200 bg-white p-5">
                <div className="flex items-center gap-2 mb-4">
                  <TrendingUp size={13} strokeWidth={1.5} className="text-[#d97706]" />
                  <div className="overline text-[#d97706]">Fastest Growing</div>
                </div>
                {(insights.fastest_growing || []).slice(0, 5).map((p, i) => (
                  <div key={p.id} className="flex items-start gap-3 mb-3 last:mb-0">
                    <span className="font-mono text-slate-300 text-xs mt-0.5 w-4 shrink-0">{i + 1}</span>
                    <div className="flex-1 min-w-0">
                      <Link to={`/citations/${p.id}`}
                        className="text-sm text-slate-800 line-clamp-2 hover:text-[#0F2847] transition-colors">{p.title}</Link>
                      <div className="text-xs mt-0.5">
                        <span className="text-[#d97706] font-mono font-medium">+{p.recent_delta} recent</span>
                        <span className="text-slate-400 ml-1">· {p.citations.toLocaleString()} total</span>
                      </div>
                    </div>
                  </div>
                ))}
                {!(insights.fastest_growing || []).length && <div className="text-sm text-slate-400">Sync to detect citation growth.</div>}
              </div>

              <div className="border border-slate-200 bg-white p-5">
                <div className="flex items-center gap-2 mb-4">
                  <Target size={13} strokeWidth={1.5} className="text-[#7c3aed]" />
                  <div className="overline text-[#7c3aed]">Influential Topics</div>
                </div>
                {(insights.influential_topics || []).length > 0 ? (
                  <div className="space-y-3">
                    {insights.influential_topics.map(({ topic, citations: c }) => (
                      <div key={topic}>
                        <div className="flex justify-between text-xs mb-1">
                          <span className="text-slate-700 capitalize truncate max-w-[60%]">{topic}</span>
                          <span className="font-mono text-slate-500">{c.toLocaleString()}</span>
                        </div>
                        <div className="h-1.5 bg-slate-100 relative">
                          <div className="absolute inset-y-0 left-0" style={{
                            width: `${Math.min(100, (c / ((insights.influential_topics[0]?.citations) || 1)) * 100)}%`,
                            background: "#7c3aed", opacity: 0.7,
                          }} />
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="text-sm text-slate-400">Derived from OpenAlex concepts on your publications.</div>
                )}
              </div>
            </div>
          </section>

          {/* ─── Feature 4: transparent impact score ──────────────────────── */}
          <section>
            <SectionHeader label="Research Impact Score" icon={Award}
              action={<span className="text-xs text-slate-400 font-mono">40 / 25 / 20 / 15 formula</span>} />
            <TransparentScore impact={impact} />
          </section>

          <DataNote>
            Citation counts are sourced from OpenAlex. Use "Sync & Track" to refresh and detect new citations.
            Delta tracking starts from your first snapshot.
          </DataNote>

          {/* ── Research Intelligence Quick Links ── */}
          <section>
            <h2 className="overline mb-5">Continue in Research Intelligence</h2>
            <div className="grid sm:grid-cols-2 lg:grid-cols-5 gap-3">
              {[
                { to: "/analytics",           label: "Analytics Overview"    },
                { to: "/citation-monitoring", label: "Citation Monitoring"   },
                { to: "/research-impact",     label: "Research Impact"       },
                { to: "/reputation",          label: "Reputation Score"      },
                { to: "/verification",        label: "Verification Center"   },
              ].map(({ to, label }) => (
                <Link key={to} to={to} className="border border-slate-200 bg-white p-4 hover:border-[#0F2847] transition-colors group block">
                  <div className="text-xs font-medium text-slate-700 group-hover:text-[#0F2847] transition-colors flex items-center justify-between">
                    {label} <ChevronRight size={12} className="text-slate-300 group-hover:text-[#0F2847]" />
                  </div>
                </Link>
              ))}
            </div>
          </section>
        </>
      )}
      </div>
    </ResearchLayout>
  );
}
