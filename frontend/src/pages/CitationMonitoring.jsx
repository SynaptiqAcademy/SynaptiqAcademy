import React, { useEffect, useState, useCallback } from "react";
import { Link } from "react-router-dom";
import { ResearchLayout } from "@/layouts";
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
import { Button } from "@/components/ds/Button";
import { Card } from "@/components/ds/Card";
import { Badge } from "@/components/ds/Badge";
import { StatCard } from "@/components/ds/StatCard";
import { DataTable } from "@/components/ds/DataTable";
import { Callout } from "@/components/ds/Alert";

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

function ScoreBar({ label, value, max = 100, color = "#0F2847" }) {
  const pct = Math.min(100, (value / max) * 100);
  return (
    <Card padding="xl">
      <div className="flex items-baseline justify-between">
        <div className="overline">{label}</div>
        <div className="font-serif text-3xl text-slate-900">{value}</div>
      </div>
      <div className="mt-3 h-1 bg-slate-100 relative">
        <div className="absolute inset-y-0 left-0" style={{ width: `${pct}%`, background: color }} />
      </div>
    </Card>
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
  return <Callout variant="warning">{children}</Callout>;
}

// ─────────────────────── gate view ───────────────────────────────────────────

function GateView() {
  return (
    <ResearchLayout title="Citation Monitoring" subtitle="Research Impact">
      <Card padding="xl" className="!p-16 flex flex-col items-center text-center gap-5">
        <Lock size={28} strokeWidth={1} className="text-slate-300" />
        <div>
          <div className="overline text-[#0F2847] mb-2">Pro Researcher plan required</div>
          <h2 className="font-serif text-2xl text-slate-900">Citation Monitoring is a Pro feature</h2>
          <p className="text-slate-500 text-sm mt-3 max-w-sm mx-auto">
            Track your citation impact, monitor publication performance, compare against your institution,
            and export detailed reports.
          </p>
        </div>
        <Button as={Link} to="/pricing" variant="primary">
          View Plans
        </Button>
      </Card>
    </ResearchLayout>
  );
}

// ─────────────────────── empty / no-data prompt ──────────────────────────────

function NoDataPrompt({ onSync, syncing }) {
  return (
    <Card padding="xl" className="!p-12 flex flex-col items-center text-center gap-5">
      <BookOpen size={32} strokeWidth={1} className="text-slate-300" />
      <div>
        <h2 className="font-serif text-xl text-slate-900">No citation data yet</h2>
        <p className="text-slate-500 text-sm mt-2 max-w-sm mx-auto">
          Connect your ORCID and sync your OpenAlex profile to populate your citation dashboard.
          Alternatively, ensure your ORCID ID is saved in your Academic Passport.
        </p>
      </div>
      <div className="flex gap-3">
        <Button onClick={onSync} disabled={syncing} variant="primary" size="sm">
          <RefreshCw size={13} className={syncing ? "animate-spin" : ""} />
          {syncing ? "Syncing…" : "Sync OpenAlex"}
        </Button>
        <Button as={Link} to="/academic-passport" variant="outline" size="sm">
          ORCID Settings
        </Button>
      </div>
    </Card>
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
    <Card padding="none" variant="ghost" className="bg-slate-50 p-4 space-y-1.5">
      <div className="flex items-start justify-between gap-2">
        <div className="text-sm font-medium text-slate-900 line-clamp-2 flex-1">{pub.title}</div>
        <Badge color={badgeColor} size="sm" className="shrink-0 font-mono">
          {badgeText}
        </Badge>
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
    </Card>
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
    <ResearchLayout
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
          <Button onClick={handleSync} disabled={syncing} data-testid={TID.citationMonitoringSyncBtn} variant="outline" size="sm">
            <RefreshCw size={12} strokeWidth={1.5} className={syncing ? "animate-spin" : ""} />{syncing ? "Syncing…" : "Sync OpenAlex"}
          </Button>
          <Button onClick={handleExport} disabled={exporting || !hasData} data-testid={TID.citationMonitoringExportBtn} variant="primary" size="sm">
            <Download size={12} strokeWidth={1.5} />{exporting ? "Exporting…" : "Export CSV"}
          </Button>
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
              <StatCard label="Total Citations" value={summary.total_citations.toLocaleString()} />
              <StatCard label="h-index" value={summary.h_index} />
              <StatCard label="i10-index" value={summary.i10_index} />
              <StatCard label="Works Count" value={summary.works_count} sub={`${summary.enriched_count} enriched with OpenAlex`} />
            </div>
          </section>

          {/* ─── research impact score ────────────────────────────────────── */}
          <section>
            <SectionHeader label="Research Impact Score" icon={Award} />
            <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-5">
              <Card padding="xl" className="lg:col-span-1 flex flex-col items-center justify-center text-center">
                <div className="overline mb-2">Composite Score</div>
                <div className="font-serif text-6xl text-slate-900 tracking-tight">{impact.score}</div>
                <div className="text-xs text-slate-400 mt-1">/ 100</div>
              </Card>
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
              <Card padding="xl">
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
                <div className="mt-6">
                  <DataTable
                    columns={[
                      { key: "year",       label: "Year" },
                      { key: "pubs",       label: "Publications",     align: "right" },
                      { key: "total",      label: "Total Citations",  align: "right" },
                      { key: "avg",        label: "Avg per Paper",    align: "right" },
                    ]}
                    rows={[...timeline].reverse().map((row) => ({
                      id: row.year,
                      year: <span className="font-mono">{row.year}</span>,
                      pubs: row.publications,
                      total: <span className="font-medium text-slate-900">{row.total_citations.toLocaleString()}</span>,
                      avg: row.avg_citations,
                    }))}
                  />
                </div>
              </Card>
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
              <DataTable
                columns={[
                  { key: "title",     label: "Title" },
                  { key: "year",      label: "Year",      align: "right" },
                  { key: "citations", label: "Citations", align: "right" },
                  { key: "type",      label: "Type",      align: "right" },
                  { key: "doi",       label: "DOI" },
                ]}
                rows={publications.map((pub) => ({
                  id: pub.id,
                  "data-testid": TID.citationMonitoringPubRow(pub.id),
                  title: (
                    <div className="max-w-xs">
                      <div className="line-clamp-2">{pub.title}</div>
                      {pub.journal && (
                        <div className="text-xs text-slate-400 mt-0.5 truncate">{pub.journal}</div>
                      )}
                    </div>
                  ),
                  year: <span className="font-mono">{pub.year || "—"}</span>,
                  citations: (
                    <span className={`font-serif text-lg ${pub.citations > 0 ? "text-slate-900" : "text-slate-300"}`}>
                      {pub.citations.toLocaleString()}
                    </span>
                  ),
                  type: (
                    <Badge variant="outline" size="sm" className="font-mono whitespace-nowrap">
                      {(pub.type || "article").replace(/_/g, " ")}
                    </Badge>
                  ),
                  doi: pub.doi ? (
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
                  ),
                }))}
              />
            </section>
          )}

          {/* ─── citation alerts ──────────────────────────────────────────── */}
          {(alerts.high_impact?.length > 0 || alerts.high_velocity?.length > 0 || alerts.recently_enriched?.length > 0) && (
            <section>
              <SectionHeader label="Citation Alerts" icon={Zap} />
              <div className="grid lg:grid-cols-3 gap-5">
                {/* high impact */}
                {alerts.high_impact?.length > 0 && (
                  <Card padding="lg" className="space-y-3">
                    <div className="flex items-center gap-2 mb-3">
                      <TrendingUp size={13} strokeWidth={1.5} className="text-[#16a34a]" />
                      <div className="overline text-[#16a34a]">High Impact Publications</div>
                    </div>
                    {alerts.high_impact.map((pub) => (
                      <AlertCard key={pub.id} pub={pub} type="high_impact" />
                    ))}
                  </Card>
                )}

                {/* high velocity */}
                {alerts.high_velocity?.length > 0 && (
                  <Card padding="lg" className="space-y-3">
                    <div className="flex items-center gap-2 mb-3">
                      <Zap size={13} strokeWidth={1.5} className="text-[#d97706]" />
                      <div className="overline text-[#d97706]">Fast-Growing Citations</div>
                    </div>
                    {alerts.high_velocity.map((pub) => (
                      <AlertCard key={pub.id} pub={pub} type="high_velocity" />
                    ))}
                  </Card>
                )}

                {/* recently enriched */}
                {alerts.recently_enriched?.length > 0 && (
                  <Card padding="lg" className="space-y-3">
                    <div className="flex items-center gap-2 mb-3">
                      <RefreshCw size={13} strokeWidth={1.5} className="text-[#2563eb]" />
                      <div className="overline text-[#2563eb]">Recently Synced</div>
                    </div>
                    {alerts.recently_enriched.map((pub) => (
                      <AlertCard key={pub.id} pub={pub} type="recently_enriched" />
                    ))}
                  </Card>
                )}
              </div>

              {/* uncited */}
              {alerts.uncited_enriched?.length > 0 && (
                <Card padding="lg" className="mt-4">
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
                </Card>
              )}
            </section>
          )}

          {/* ─── author impact summary ────────────────────────────────────── */}
          <section>
            <SectionHeader label="Author Impact Summary" icon={Award} />
            <Card padding="xl">
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
            </Card>
          </section>

          {/* ─── institution comparison ───────────────────────────────────── */}
          {instCmp && (
            <section>
              <SectionHeader label="Institution Comparison" icon={Building2} />
              <Card padding="xl" className="space-y-6">
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
              </Card>
            </section>
          )}

          {/* ─── data provenance note ─────────────────────────────────────── */}
          <div>
            <DataNote>{data.data_note}</DataNote>
          </div>

        </>
      )}
    </div>
    </ResearchLayout>
  );
}
