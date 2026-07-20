import React, { useEffect, useState, useCallback } from "react";
import { Link } from "react-router-dom";
import { AnalyticsLayout } from "@/layouts";
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
} from "recharts";
import {
  Lock, RotateCcw, Download, AlertTriangle, TrendingUp, Award,
  BookOpen, Zap, CheckCircle2, XCircle, RefreshCw, ExternalLink,
  Building2, Info, ChevronRight,
} from "lucide-react";
import api from "../lib/api";
import { TID } from "../lib/testIds";
import { NAVY, WARM } from "@/lib/tokens";
import { Spinner } from "@/components/ds/LoadingState";

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

// ─────────────────────── shared primitives ───────────────────────────────────

function Stat({ label, value, sub }) {
  return (
    <div className="border border-slate-200 bg-white p-6">
      <div className="overline">{label}</div>
      <div className="font-serif text-5xl text-slate-900 mt-3 tracking-tight">{value}</div>
      {sub && <div className="text-xs text-slate-500 mt-2">{sub}</div>}
    </div>
  );
}

function ScoreBar({ label, value, max = 100, color = "#0F2847" }) {
  const pct = Math.min(100, (value / max) * 100);
  return (
    <div className="border border-slate-200 bg-white p-6">
      <div className="flex items-baseline justify-between">
        <div className="overline">{label}</div>
        <div className="font-serif text-3xl text-slate-900">{value}</div>
      </div>
      <div className="mt-3 h-1 bg-slate-100 relative">
        <div className="absolute inset-y-0 left-0" style={{ width: `${pct}%`, background: color }} />
      </div>
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

// ─────────────────────── gate view ───────────────────────────────────────────

function GateView() {
  return (
    <div className="space-y-6">
      <header className="border-b border-slate-200 pb-6">
        <div className="overline">Research Impact</div>
        <h1 className="font-serif text-5xl text-slate-900 mt-2">Citation Monitoring</h1>
      </header>
      <div className="border border-slate-200 bg-white p-16 flex flex-col items-center text-center gap-5">
        <Lock size={28} strokeWidth={1} className="text-slate-300" />
        <div>
          <div className="overline text-[#0F2847] mb-2">Pro Researcher plan required</div>
          <h2 className="font-serif text-2xl text-slate-900">Citation Monitoring is a Pro feature</h2>
          <p className="text-slate-500 text-sm mt-3 max-w-sm mx-auto">
            Track your citation impact, monitor publication performance, compare against your institution,
            and export detailed reports.
          </p>
        </div>
        <Link
          to="/pricing"
          className="inline-block bg-[#0F2847] text-white text-sm px-6 py-2.5 hover:opacity-90 transition-opacity"
        >
          View Plans
        </Link>
      </div>
    </div>
  );
}

// ─────────────────────── empty / no-data prompt ──────────────────────────────

function NoDataPrompt({ onSync, syncing }) {
  return (
    <div className="border border-slate-200 bg-white p-12 flex flex-col items-center text-center gap-5">
      <BookOpen size={32} strokeWidth={1} className="text-slate-300" />
      <div>
        <h2 className="font-serif text-xl text-slate-900">No citation data yet</h2>
        <p className="text-slate-500 text-sm mt-2 max-w-sm mx-auto">
          Connect your ORCID and sync your OpenAlex profile to populate your citation dashboard.
          Alternatively, ensure your ORCID ID is saved in your Academic Passport.
        </p>
      </div>
      <div className="flex gap-3">
        <button
          onClick={onSync}
          disabled={syncing}
          className="flex items-center gap-2 bg-[#0F2847] text-white text-sm px-5 py-2 hover:opacity-90 disabled:opacity-50 transition-opacity"
        >
          <RefreshCw size={13} className={syncing ? "animate-spin" : ""} />
          {syncing ? "Syncing…" : "Sync OpenAlex"}
        </button>
        <Link
          to="/academic-passport"
          className="flex items-center gap-2 border border-slate-300 text-slate-600 text-sm px-5 py-2 hover:border-[#0F2847] hover:text-[#0F2847] transition-colors"
        >
          ORCID Settings
        </Link>
      </div>
    </div>
  );
}

// ─────────────────────── custom chart tooltip ─────────────────────────────────

function ChartTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null;
  return (
    <div className="border border-slate-200 bg-white shadow-sm px-3 py-2 text-xs">
      <div className="font-medium text-slate-900 mb-1">{label}</div>
      {payload.map((p) => (
        <div key={p.dataKey} className="flex items-center gap-2 text-slate-600">
          <span className="w-2 h-2 rounded-full inline-block" style={{ background: p.fill }} />
          {p.name}: {p.value}
        </div>
      ))}
    </div>
  );
}

// ─────────────────────── alert card ──────────────────────────────────────────

function AlertCard({ pub, type }) {
  const badgeText = {
    recently_enriched: "Just Tracked",
    high_impact:       "High Impact",
    high_velocity:     "Fast Growing",
    uncited_enriched:  "Uncited",
  }[type] || type;

  const badgeColor = {
    recently_enriched: "#2563eb",
    high_impact:       "#16a34a",
    high_velocity:     "#d97706",
    uncited_enriched:  "#64748b",
  }[type] || "#64748b";

  return (
    <div className="border border-slate-100 bg-slate-50 p-4 space-y-1.5">
      <div className="flex items-start justify-between gap-2">
        <div className="text-sm font-medium text-slate-900 line-clamp-2 flex-1">{pub.title}</div>
        <span className="shrink-0 text-xs border px-1.5 py-0.5 font-mono"
          style={{ borderColor: badgeColor, color: badgeColor }}>
          {badgeText}
        </span>
      </div>
      <div className="flex items-center gap-3 text-xs text-slate-500">
        {pub.year && <span>{pub.year}</span>}
        <span className="font-mono text-slate-700">{pub.citations} citation{pub.citations !== 1 ? "s" : ""}</span>
        {pub.doi && (
          <a href={`https://doi.org/${pub.doi}`} target="_blank" rel="noopener noreferrer"
            className="flex items-center gap-0.5 hover:text-[#0F2847] transition-colors">
            DOI <ExternalLink size={10} />
          </a>
        )}
      </div>
    </div>
  );
}

// ─────────────────────── institution comparison ───────────────────────────────

function PercentileBar({ value, label }) {
  return (
    <div>
      <div className="flex justify-between text-xs mb-1">
        <span className="text-slate-500">{label}</span>
        <span className="font-mono text-slate-700">{value}th percentile</span>
      </div>
      <div className="h-2 bg-slate-100 relative">
        <div className="absolute inset-y-0 left-0 bg-[#0F2847]" style={{ width: `${value}%` }} />
        <div className="absolute inset-y-0 w-0.5 bg-white" style={{ left: `${value}%` }} />
      </div>
    </div>
  );
}

// ─────────────────────── main page ───────────────────────────────────────────

export default function CitationMonitoring() {
  const [data, setData] = useState(null);
  const [gated, setGated] = useState(false);
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState(false);
  const [syncMsg, setSyncMsg] = useState(null);
  const [exporting, setExporting] = useState(false);

  const load = useCallback(() => {
    setLoading(true);
    api.get("/citation-monitoring/dashboard")
      .then((r) => setData(r.data))
      .catch((err) => {
        if (err?.response?.status === 402) setGated(true);
      })
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => { load(); }, [load]);

  const handleSync = async () => {
    setSyncing(true);
    setSyncMsg(null);
    try {
      await api.post("/reputation/sync-openalex");
      setSyncMsg({ ok: true, text: "OpenAlex synced. Refreshing dashboard…" });
      setTimeout(() => { load(); setSyncMsg(null); }, 1500);
    } catch (err) {
      const detail = err?.response?.data?.detail;
      setSyncMsg({ ok: false, text: detail || "Sync failed. Ensure your ORCID is set in profile settings." });
    } finally {
      setSyncing(false);
    }
  };

  const handleExport = async () => {
    setExporting(true);
    try {
      const resp = await api.get("/citation-monitoring/export", { responseType: "blob" });
      const url = URL.createObjectURL(resp.data);
      const a = document.createElement("a");
      a.href = url;
      a.download = `citations_${new Date().toISOString().slice(0, 10)}.csv`;
      a.click();
      URL.revokeObjectURL(url);
    } catch {}
    setExporting(false);
  };

  if (gated) return <GateView />;
  if (loading) return <div className="py-12 flex justify-center"><Spinner size={20} /></div>;

  const summary        = data?.summary || {};
  const publications   = data?.publications || [];
  const timeline       = data?.timeline || [];
  const alerts         = data?.alerts || {};
  const impact         = data?.impact_score || {};
  const author         = data?.author_summary || {};
  const instCmp        = data?.institution_comparison;

  const hasData = summary.has_data || publications.length > 0;
  const needsSync = summary.needs_sync;

  const timelineMax = Math.max(...timeline.map((t) => t.total_citations), 1);

  return (
    <AnalyticsLayout
      data-testid={TID.citationMonitoringDashboard}
      title="Citation Monitoring"
      subtitle={
        <>
          Tracking citation impact for <strong style={{ color: "#0F2847" }}>{author.full_name || "your account"}</strong>
          {author.institution ? ` · ${author.institution}` : ""}.
          {summary.last_synced && <span style={{ color: "#94A3B8", marginLeft: 6 }}>Last synced {new Date(summary.last_synced).toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric" })}.</span>}
          {syncMsg && (
            <span className={`ml-3 inline-flex items-center gap-1 text-sm ${syncMsg.ok ? "text-green-700" : "text-red-600"}`}>
              {syncMsg.ok ? <CheckCircle2 size={12} /> : <XCircle size={12} />}
              {syncMsg.text}
            </span>
          )}
          {needsSync && !syncing && (
            <span style={{ display: "block", marginTop: 6, fontSize: 12, color: "#92400E" }}>
              {summary.last_synced
                ? "Your OpenAlex data is over 30 days old. Sync to get the latest citation counts."
                : "No OpenAlex data found. Click 'Sync OpenAlex' to populate your citation dashboard."}
            </span>
          )}
        </>
      }
      nav={<IntelNav current="/citation-monitoring" />}
      actions={
        <>
          <button onClick={handleSync} disabled={syncing} data-testid={TID.citationMonitoringSyncBtn}
            style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 12, color: "#64748B", padding: "8px 14px", border: "1px solid rgba(15,23,42,0.08)", background: "#fff", cursor: "pointer", opacity: syncing ? 0.5 : 1 }}>
            <RefreshCw size={12} strokeWidth={1.5} className={syncing ? "animate-spin" : ""} />{syncing ? "Syncing…" : "Sync OpenAlex"}
          </button>
          <button onClick={handleExport} disabled={exporting || !hasData} data-testid={TID.citationMonitoringExportBtn}
            style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 12, color: "#fff", padding: "8px 14px", background: "#0F2847", border: "none", cursor: "pointer", opacity: (exporting || !hasData) ? 0.5 : 1 }}>
            <Download size={12} strokeWidth={1.5} />{exporting ? "Exporting…" : "Export CSV"}
          </button>
        </>
      }
    >
      <div className="space-y-10">
      {!hasData ? (
        <NoDataPrompt onSync={handleSync} syncing={syncing} />
      ) : (
        <>
          {/* ─── citation dashboard ────────────────────────────────────────── */}
          <section>
            <SectionHeader label="Citation Dashboard" icon={BarChart} />
            <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-5">
              <Stat label="Total Citations" value={summary.total_citations.toLocaleString()} />
              <Stat label="h-index" value={summary.h_index} />
              <Stat label="i10-index" value={summary.i10_index} />
              <Stat label="Works Count" value={summary.works_count} sub={`${summary.enriched_count} enriched with OpenAlex`} />
            </div>
          </section>

          {/* ─── research impact score ────────────────────────────────────── */}
          <section>
            <SectionHeader label="Research Impact Score" icon={Award} />
            <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-5">
              <div className="lg:col-span-1 border border-slate-200 bg-white p-6 flex flex-col items-center justify-center text-center">
                <div className="overline mb-2">Composite Score</div>
                <div className="font-serif text-6xl text-slate-900 tracking-tight">{impact.score}</div>
                <div className="text-xs text-slate-400 mt-1">/ 100</div>
              </div>
              <div className="lg:col-span-3 grid sm:grid-cols-2 gap-5">
                <ScoreBar label="Citation Impact"  value={impact.components?.citation_impact || 0} />
                <ScoreBar label="H-Index Score"    value={impact.components?.h_index_score   || 0} />
                <ScoreBar label="Research Breadth" value={impact.components?.breadth_score   || 0} />
                <ScoreBar label="Data Coverage"    value={impact.components?.coverage_score  || 0} />
              </div>
            </div>
            <div className="mt-3">
              <DataNote>
                Composite score (0–100) derived from your OpenAlex citation metrics.
                Citation impact (40%), h-index (30%), research breadth (20%), enrichment coverage (10%).
              </DataNote>
            </div>
          </section>

          {/* ─── citation timeline ────────────────────────────────────────── */}
          {timeline.length > 0 && (
            <section>
              <SectionHeader label="Citation Timeline by Publication Year" icon={TrendingUp} />
              <div className="border border-slate-200 bg-white p-6">
                <p className="text-xs text-slate-500 mb-4">
                  Total citations accumulated by publications from each year.
                  Each bar represents citations received by papers published that year, as of your last OpenAlex sync.
                </p>
                <ResponsiveContainer width="100%" height={240}>
                  <BarChart data={timeline} margin={{ top: 4, right: 4, left: 0, bottom: 4 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" vertical={false} />
                    <XAxis
                      dataKey="year"
                      tick={{ fontSize: 11, fill: "#64748b", fontFamily: "inherit" }}
                      axisLine={false} tickLine={false}
                    />
                    <YAxis
                      tick={{ fontSize: 11, fill: "#64748b", fontFamily: "inherit" }}
                      axisLine={false} tickLine={false} width={40}
                    />
                    <Tooltip content={<ChartTooltip />} cursor={{ fill: "#f8fafc" }} />
                    <Bar dataKey="total_citations" name="Total Citations" fill="#0F2847" radius={[2, 2, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>

                {/* yearly table */}
                <div className="mt-6 overflow-x-auto">
                  <table className="w-full text-sm border-collapse">
                    <thead>
                      <tr className="border-b border-slate-200">
                        <th className="text-left py-2 overline font-normal text-slate-500">Year</th>
                        <th className="text-right py-2 overline font-normal text-slate-500">Publications</th>
                        <th className="text-right py-2 overline font-normal text-slate-500">Total Citations</th>
                        <th className="text-right py-2 overline font-normal text-slate-500">Avg per Paper</th>
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

          {/* ─── publication impact table ─────────────────────────────────── */}
          {publications.length > 0 && (
            <section>
              <SectionHeader
                label="Publication Impact"
                icon={BookOpen}
                action={
                  <span className="text-xs text-slate-400 font-mono">{publications.length} publications · sorted by citations</span>
                }
              />
              <div className="border border-slate-200 bg-white overflow-x-auto">
                <table className="w-full text-sm border-collapse">
                  <thead>
                    <tr className="border-b border-slate-200 bg-slate-50">
                      <th className="text-left px-4 py-3 overline font-normal text-slate-500">Title</th>
                      <th className="text-right px-4 py-3 overline font-normal text-slate-500 whitespace-nowrap">Year</th>
                      <th className="text-right px-4 py-3 overline font-normal text-slate-500 whitespace-nowrap">Citations</th>
                      <th className="text-right px-4 py-3 overline font-normal text-slate-500 whitespace-nowrap">Type</th>
                      <th className="px-4 py-3 overline font-normal text-slate-500 whitespace-nowrap">DOI</th>
                    </tr>
                  </thead>
                  <tbody>
                    {publications.map((pub) => (
                      <tr
                        key={pub.id}
                        data-testid={TID.citationMonitoringPubRow(pub.id)}
                        className="border-b border-slate-100 hover:bg-slate-50 transition-colors"
                      >
                        <td className="px-4 py-3 text-slate-800 max-w-xs">
                          <div className="line-clamp-2">{pub.title}</div>
                          {pub.journal && (
                            <div className="text-xs text-slate-400 mt-0.5 truncate">{pub.journal}</div>
                          )}
                        </td>
                        <td className="px-4 py-3 text-right font-mono text-slate-600">{pub.year || "—"}</td>
                        <td className="px-4 py-3 text-right">
                          <span className={`font-serif text-lg ${pub.citations > 0 ? "text-slate-900" : "text-slate-300"}`}>
                            {pub.citations.toLocaleString()}
                          </span>
                        </td>
                        <td className="px-4 py-3 text-right">
                          <span className="text-xs border border-slate-200 text-slate-500 px-1.5 py-0.5 font-mono whitespace-nowrap">
                            {(pub.type || "article").replace(/_/g, " ")}
                          </span>
                        </td>
                        <td className="px-4 py-3">
                          {pub.doi ? (
                            <a
                              href={`https://doi.org/${pub.doi}`}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="flex items-center gap-0.5 text-xs text-slate-500 hover:text-[#0F2847] transition-colors"
                            >
                              {pub.doi.substring(0, 20)}{pub.doi.length > 20 ? "…" : ""}
                              <ExternalLink size={10} />
                            </a>
                          ) : (
                            <span className="text-xs text-slate-300">—</span>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </section>
          )}

          {/* ─── citation alerts ──────────────────────────────────────────── */}
          {(alerts.high_impact?.length > 0 || alerts.high_velocity?.length > 0 || alerts.recently_enriched?.length > 0) && (
            <section>
              <SectionHeader label="Citation Alerts" icon={Zap} />
              <div className="grid lg:grid-cols-3 gap-5">
                {/* high impact */}
                {alerts.high_impact?.length > 0 && (
                  <div className="border border-slate-200 bg-white p-5 space-y-3">
                    <div className="flex items-center gap-2 mb-3">
                      <TrendingUp size={13} strokeWidth={1.5} className="text-[#16a34a]" />
                      <div className="overline text-[#16a34a]">High Impact Publications</div>
                    </div>
                    {alerts.high_impact.map((pub) => (
                      <AlertCard key={pub.id} pub={pub} type="high_impact" />
                    ))}
                  </div>
                )}

                {/* high velocity */}
                {alerts.high_velocity?.length > 0 && (
                  <div className="border border-slate-200 bg-white p-5 space-y-3">
                    <div className="flex items-center gap-2 mb-3">
                      <Zap size={13} strokeWidth={1.5} className="text-[#d97706]" />
                      <div className="overline text-[#d97706]">Fast-Growing Citations</div>
                    </div>
                    {alerts.high_velocity.map((pub) => (
                      <AlertCard key={pub.id} pub={pub} type="high_velocity" />
                    ))}
                  </div>
                )}

                {/* recently enriched */}
                {alerts.recently_enriched?.length > 0 && (
                  <div className="border border-slate-200 bg-white p-5 space-y-3">
                    <div className="flex items-center gap-2 mb-3">
                      <RefreshCw size={13} strokeWidth={1.5} className="text-[#2563eb]" />
                      <div className="overline text-[#2563eb]">Recently Synced</div>
                    </div>
                    {alerts.recently_enriched.map((pub) => (
                      <AlertCard key={pub.id} pub={pub} type="recently_enriched" />
                    ))}
                  </div>
                )}
              </div>

              {/* uncited */}
              {alerts.uncited_enriched?.length > 0 && (
                <div className="mt-4 border border-slate-200 bg-white p-5">
                  <div className="flex items-center gap-2 mb-3">
                    <AlertTriangle size={13} strokeWidth={1.5} className="text-slate-400" />
                    <div className="overline text-slate-500">Tracked but Uncited</div>
                  </div>
                  <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-3">
                    {alerts.uncited_enriched.map((pub) => (
                      <AlertCard key={pub.id} pub={pub} type="uncited_enriched" />
                    ))}
                  </div>
                  <p className="text-xs text-slate-400 mt-3">
                    These publications have been confirmed on OpenAlex but have no recorded citations yet.
                    Consider sharing, submitting to preprint servers, or promoting through collaborative networks.
                  </p>
                </div>
              )}
            </section>
          )}

          {/* ─── author impact summary ────────────────────────────────────── */}
          <section>
            <SectionHeader label="Author Impact Summary" icon={Award} />
            <div className="border border-slate-200 bg-white p-6">
              <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-6">
                <div className="space-y-1">
                  <div className="overline text-slate-500">Researcher</div>
                  <div className="font-serif text-lg text-slate-900">{author.full_name || "—"}</div>
                  {author.institution && (
                    <div className="text-xs text-slate-500">{author.institution}</div>
                  )}
                </div>
                <div className="space-y-1">
                  <div className="overline text-slate-500">OpenAlex Profile</div>
                  {author.openalex_id ? (
                    <a
                      href={author.openalex_id}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="flex items-center gap-1 text-sm text-[#0F2847] hover:underline"
                    >
                      View on OpenAlex <ExternalLink size={11} />
                    </a>
                  ) : (
                    <div className="text-sm text-slate-400">Not linked</div>
                  )}
                </div>
                <div className="space-y-1">
                  <div className="overline text-slate-500">Total Citations</div>
                  <div className="font-serif text-3xl text-slate-900">{author.total_citations?.toLocaleString() || 0}</div>
                </div>
                <div className="space-y-1">
                  <div className="overline text-slate-500">h-index / i10-index</div>
                  <div className="font-serif text-3xl text-slate-900">
                    {author.h_index} <span className="text-slate-300 text-2xl">/</span> {author.i10_index}
                  </div>
                </div>
              </div>
            </div>
          </section>

          {/* ─── institution comparison ───────────────────────────────────── */}
          {instCmp && (
            <section>
              <SectionHeader label="Institution Comparison" icon={Building2} />
              <div className="border border-slate-200 bg-white p-6 space-y-6">
                <div className="flex items-center justify-between">
                  <div>
                    <div className="font-serif text-lg text-slate-900">{instCmp.institution_name || "Your Institution"}</div>
                    <div className="text-xs text-slate-500 mt-0.5">{instCmp.member_count} members with OpenAlex data</div>
                  </div>
                </div>
                <div className="grid sm:grid-cols-2 gap-8">
                  <div className="space-y-4">
                    <PercentileBar value={instCmp.user_citation_percentile} label="Citation percentile" />
                    <div className="grid grid-cols-2 gap-4 text-sm">
                      <div>
                        <div className="overline text-slate-500 mb-0.5">Your Citations</div>
                        <div className="font-serif text-2xl text-slate-900">{summary.total_citations.toLocaleString()}</div>
                      </div>
                      <div>
                        <div className="overline text-slate-500 mb-0.5">Institution Avg</div>
                        <div className="font-serif text-2xl text-slate-600">{instCmp.avg_citations.toLocaleString()}</div>
                      </div>
                      <div>
                        <div className="overline text-slate-500 mb-0.5">Median</div>
                        <div className="font-serif text-2xl text-slate-600">{instCmp.median_citations.toLocaleString()}</div>
                      </div>
                    </div>
                  </div>
                  <div className="space-y-4">
                    <PercentileBar value={instCmp.user_h_percentile} label="h-index percentile" />
                    <div className="grid grid-cols-2 gap-4 text-sm">
                      <div>
                        <div className="overline text-slate-500 mb-0.5">Your h-index</div>
                        <div className="font-serif text-2xl text-slate-900">{summary.h_index}</div>
                      </div>
                      <div>
                        <div className="overline text-slate-500 mb-0.5">Institution Avg</div>
                        <div className="font-serif text-2xl text-slate-600">{instCmp.avg_h_index}</div>
                      </div>
                      <div>
                        <div className="overline text-slate-500 mb-0.5">Median</div>
                        <div className="font-serif text-2xl text-slate-600">{instCmp.median_h_index}</div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </section>
          )}

          {/* ─── data provenance note ─────────────────────────────────────── */}
          <div>
            <DataNote>{data.data_note}</DataNote>
          </div>

          {/* ── Research Intelligence Quick Links ── */}
          <section>
            <h2 className="overline mb-5">Continue in Research Intelligence</h2>
            <div className="grid sm:grid-cols-2 lg:grid-cols-5 gap-3">
              {[
                { to: "/analytics",       label: "Analytics Overview" },
                { to: "/citations",       label: "Citation Tracker"   },
                { to: "/research-impact", label: "Research Impact"    },
                { to: "/reputation",      label: "Reputation Score"   },
                { to: "/verification",    label: "Verification"       },
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
    </AnalyticsLayout>
  );
}
