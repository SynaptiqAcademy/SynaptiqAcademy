import React, { useState, useEffect, useCallback } from "react";
import api from "@/lib/api";
import { NAVY, TEAL, EMERALD, VIOLET } from "@/lib/tokens";
import { AdministrationLayout } from "@/layouts";
import {
  RefreshCw, Users, Award, BookOpen, BarChart2,
  Globe, Building2, TrendingUp,
} from "lucide-react";
import {
  Button, Card, StatCard, MiniBar, BarChart, DataTable, NavTabs,
  ErrorState, EmptyState, Skeleton, SkeletonCard,
} from "@/components/ds";

// ── Constants ──────────────────────────────────────────────────────────────────

const SIS_BUCKETS = [
  { label: "New Researcher",       range: "0–499",    key: "new_researcher" },
  { label: "Emerging Scholar",     range: "500–999",  key: "emerging_scholar" },
  { label: "Rising Scholar",       range: "1000–2499",key: "rising_scholar" },
  { label: "Established Researcher", range: "2500–4999", key: "established_researcher" },
  { label: "Senior Scholar",       range: "5000–6999",key: "senior_scholar" },
  { label: "Distinguished Researcher", range: "7000–8999", key: "distinguished_researcher" },
  { label: "Eminent Scholar",      range: "9000+",    key: "eminent_scholar" },
];

const BUCKET_COLORS = [
  "#94A3B8", "#64748B", "#0891B2", NAVY,
  VIOLET, "#D97706", "#D97706",
];

const METRIC_OPTIONS = [
  { key: "sis_score", label: "SIS Score" },
  { key: "h_index",   label: "H-Index" },
  { key: "citations", label: "Citations" },
  { key: "collaborations", label: "Collaborations" },
];

// ── Helpers ───────────────────────────────────────────────────────────────────

function fmtNum(val) {
  if (val == null) return "—";
  return Number(val).toLocaleString();
}

function fmt(val) {
  return val ?? "—";
}

function pct(value, max) {
  if (!max) return 0;
  return Math.min(100, Math.round((value / max) * 100));
}

// ── Hook: fetch admin impact data ────────────────────────────────────────────

function useAdminImpact(path) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await api.get(`/admin/impact/${path}`);
      setData(res.data);
    } catch (e) {
      setError(e?.response?.data?.detail || "Failed to load.");
    } finally {
      setLoading(false);
    }
  }, [path]);

  useEffect(() => { load(); }, [load]);

  return { data, loading, error, refetch: load };
}

// ── KPI Card ──────────────────────────────────────────────────────────────────

function KpiCard({ label, value, sub, icon: Icon, loading, highlight }) {
  return (
    <StatCard
      label={label}
      value={loading ? <Skeleton height="h-7" width="w-16" /> : value}
      sub={loading ? undefined : sub}
      icon={Icon ? <Icon /> : undefined}
      highlight={highlight}
    />
  );
}

// ── Sortable table header (drives DataTable's onSort) ─────────────────────────
// DataTable's own click-to-toggle defaults to "asc" on a newly-selected
// column; this page's original behavior always starts a freshly-selected
// column at "desc" (ranking metrics read best-first). `handleSort` below
// reimplements that exact toggle rule and DataTable's onSort callback just
// forwards the clicked key into it, discarding DataTable's own guess at dir.

// ─────────────────────────────────────────────────────────────────────────────
// ── MAIN PAGE ─────────────────────────────────────────────────────────────────
// ─────────────────────────────────────────────────────────────────────────────

export default function AdminImpactCenter() {
  // Data fetching
  const { data: statsData, loading: statsLoading, error: statsError, refetch: refetchStats } = useAdminImpact("stats");
  const { data: topData,   loading: topLoading,   error: topError,   refetch: refetchTop }   = useAdminImpact("top-researchers");
  const { data: trendData, loading: trendLoading, error: trendError, refetch: refetchTrends } = useAdminImpact("growth-trends");
  const { data: areaData,  loading: areaLoading,  error: areaError,  refetch: refetchAreas }  = useAdminImpact("research-areas");
  const { data: instData,  loading: instLoading,  error: instError,  refetch: refetchInst }   = useAdminImpact("top-institutions");
  const { data: countryData, loading: countryLoading, error: countryError, refetch: refetchCountries } = useAdminImpact("top-countries");

  // UI state
  const [metricKey, setMetricKey] = useState("sis_score");
  const [refreshingAll, setRefreshingAll] = useState(false);
  const [refreshMsg, setRefreshMsg] = useState(null);
  const [sort, setSort] = useState({ key: "sis_score", dir: "desc" });

  const handleSort = (key) => {
    setSort((prev) => ({
      key,
      dir: prev.key === key && prev.dir === "desc" ? "asc" : "desc",
    }));
  };

  const handleRefreshAll = async () => {
    setRefreshingAll(true);
    setRefreshMsg(null);
    try {
      const res = await api.post("/admin/impact/refresh-all");
      const count = res.data?.researchers_queued || res.data?.count || "all";
      setRefreshMsg(`Refreshing ${typeof count === "number" ? fmtNum(count) : count} researchers…`);
      // Refetch stats after a short delay
      setTimeout(() => {
        refetchStats();
        refetchTop();
        setRefreshMsg(null);
      }, 3000);
    } catch (e) {
      setRefreshMsg(e?.response?.data?.detail || "Failed to trigger refresh.");
    } finally {
      setRefreshingAll(false);
    }
  };

  // Derived data
  const stats = statsData || {};
  const distribution = stats.distribution || {};
  const topResearchers = Array.isArray(topData?.researchers) ? topData.researchers :
                         Array.isArray(topData) ? topData : [];
  const growthTrends = Array.isArray(trendData?.monthly) ? trendData.monthly :
                       Array.isArray(trendData) ? trendData : [];
  const researchAreas = Array.isArray(areaData?.areas) ? areaData.areas :
                        Array.isArray(areaData) ? areaData : [];
  const topInstitutions = Array.isArray(instData?.institutions) ? instData.institutions :
                          Array.isArray(instData) ? instData : [];
  const topCountries = Array.isArray(countryData?.countries) ? countryData.countries :
                       Array.isArray(countryData) ? countryData : [];

  // Sort researchers
  const sortedResearchers = [...topResearchers].sort((a, b) => {
    const aVal = a[sort.key] ?? 0;
    const bVal = b[sort.key] ?? 0;
    return sort.dir === "asc" ? aVal - bVal : bVal - aVal;
  });

  const maxBucketCount = Math.max(...SIS_BUCKETS.map((b) => distribution[b.key] || 0), 1);
  const maxAreaSIS = Math.max(...researchAreas.map((a) => a.avg_sis || 0), 1);
  const maxInstSIS = Math.max(...topInstitutions.map((i) => i.avg_sis || 0), 1);
  const maxCountrySIS = Math.max(...topCountries.map((c) => c.avg_sis || 0), 1);

  // Rows for the Top Researchers DataTable — a synthetic `_rank` field carries
  // the "#" column since DataTable's render(value, row) doesn't expose the
  // row index.
  const researcherRows = sortedResearchers.slice(0, 50).map((r, idx) => ({ ...r, _rank: idx + 1 }));

  const researcherColumns = [
    { key: "_rank", label: "#", width: 32, render: (v) => <span className="text-slate-400 text-xs">{v}</span> },
    {
      key: "name", label: "Researcher",
      render: (_v, row) => (
        <div>
          <div className="font-medium text-slate-800 text-xs">{fmt(row.full_name || row.name)}</div>
          {row.role && <div className="text-[10px] text-slate-400 mt-0.5">{row.role}</div>}
        </div>
      ),
    },
    { key: "institution", label: "Institution", maxWidth: 180, render: (v) => fmt(v) },
    { key: "country", label: "Country", render: (v) => fmt(v) },
    {
      key: "sis_score", label: "SIS Score", sortable: true,
      render: (v) => <span className="font-semibold" style={{ color: TEAL }}>{fmtNum(v)}</span>,
    },
    { key: "h_index", label: "H-Index", sortable: true, render: (v) => fmt(v) },
    { key: "publications", label: "Publications", sortable: true, render: (v) => fmtNum(v) },
  ];

  const institutionColumns = [
    {
      key: "name", label: "Institution",
      render: (v, row) => (
        <div>
          <div className="text-slate-700 truncate max-w-[180px]">{fmt(v)}</div>
          {row.country && <div className="text-slate-400 text-[9px]">{row.country}</div>}
        </div>
      ),
    },
    { key: "researcher_count", label: "Researchers", render: (v, row) => fmtNum(v || row.researchers) },
    {
      key: "avg_sis", label: "Avg SIS",
      render: (v) => (
        <div className="flex items-center gap-2">
          <span className="font-semibold" style={{ color: TEAL }}>{fmtNum(v)}</span>
          <MiniBar value={v || 0} max={maxInstSIS} height={4} color={TEAL} style={{ flex: 1, minWidth: 40 }} />
        </div>
      ),
    },
  ];

  const countryColumns = [
    { key: "country", label: "Country", render: (v) => <span className="text-slate-700">{fmt(v)}</span> },
    { key: "researcher_count", label: "Researchers", render: (v, row) => fmtNum(v || row.researchers) },
    {
      key: "avg_sis", label: "Avg SIS",
      render: (v) => (
        <div className="flex items-center gap-2">
          <span className="font-semibold" style={{ color: TEAL }}>{fmtNum(v)}</span>
          <MiniBar value={v || 0} max={maxCountrySIS} height={4} color={TEAL} style={{ flex: 1, minWidth: 40 }} />
        </div>
      ),
    },
  ];

  return (
    <AdministrationLayout
      title="Research Impact Center"
      subtitle="Platform-wide Synaptiq Impact Score analytics"
      actions={
        <div className="flex items-center gap-3">
          {refreshMsg && (
            <span className="text-xs animate-pulse" style={{ color: TEAL }}>{refreshMsg}</span>
          )}
          <Button variant="hero" size="md" onClick={handleRefreshAll} loading={refreshingAll}>
            <RefreshCw size={12} className={refreshingAll ? "animate-spin" : ""} />
            {refreshingAll ? "Triggering…" : "Refresh All Impact Scores"}
          </Button>
        </div>
      }
    >
      <div className="space-y-10">

        {/* ══════════════════════════════════════════════════════════════
            SECTION 1: PLATFORM KPIs
        ══════════════════════════════════════════════════════════════ */}
        <section>
          <div className="text-xs font-semibold uppercase tracking-widest text-slate-500 mb-3">
            Platform Overview
          </div>
          {statsError ? (
            <ErrorState message={statsError} onRetry={refetchStats} />
          ) : (
            <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4">
              <KpiCard
                label="Researchers Scored"
                value={fmtNum(stats.researchers_scored || stats.total_researchers)}
                icon={Users}
                loading={statsLoading}
              />
              <KpiCard
                label="Platform Avg SIS"
                value={fmtNum(stats.avg_sis || stats.platform_avg_sis)}
                sub="out of 10,000"
                icon={Award}
                highlight
                loading={statsLoading}
              />
              <KpiCard
                label="Platform Avg H-Index"
                value={fmt(stats.avg_h_index || stats.platform_avg_h_index)}
                icon={BarChart2}
                loading={statsLoading}
              />
              <KpiCard
                label="Total Publications"
                value={fmtNum(stats.total_publications)}
                sub="platform-wide"
                icon={BookOpen}
                loading={statsLoading}
              />
            </div>
          )}
        </section>

        {/* ══════════════════════════════════════════════════════════════
            SECTION 2: SIS DISTRIBUTION
        ══════════════════════════════════════════════════════════════ */}
        <section>
          <div className="text-xs font-semibold uppercase tracking-widest text-slate-500 mb-3">
            SIS Distribution by Level
          </div>
          {statsLoading ? (
            <SkeletonCard rows={7} />
          ) : statsError ? (
            <ErrorState message={statsError} onRetry={refetchStats} />
          ) : (
            <Card padding="lg">
              <div className="space-y-3">
                {SIS_BUCKETS.map((bucket, idx) => {
                  const count = distribution[bucket.key] || distribution[bucket.label] || 0;
                  return (
                    <div key={bucket.key}>
                      <div className="flex items-center justify-between mb-1">
                        <span className="text-xs text-slate-500 truncate max-w-[65%]">{`${bucket.label} (${bucket.range})`}</span>
                        <span className="text-xs text-slate-700 font-medium">{fmtNum(count)}</span>
                      </div>
                      <MiniBar value={count} max={maxBucketCount} height={8} color={BUCKET_COLORS[idx]} />
                      <div className="text-[10px] text-slate-400 mt-0.5">{fmtNum(count)} researchers</div>
                    </div>
                  );
                })}
              </div>
            </Card>
          )}
        </section>

        {/* ══════════════════════════════════════════════════════════════
            SECTION 3: TOP RESEARCHERS TABLE
        ══════════════════════════════════════════════════════════════ */}
        <section>
          <div className="flex items-center justify-between mb-3 flex-wrap gap-3">
            <div className="text-xs font-semibold uppercase tracking-widest text-slate-500">
              Top Researchers
            </div>
            <div className="flex items-center gap-2">
              <span className="text-xs text-slate-400">Sort by:</span>
              <NavTabs
                variant="pill"
                size="sm"
                tabs={METRIC_OPTIONS.map((opt) => ({ id: opt.key, label: opt.label }))}
                active={metricKey}
                onChange={(key) => { setMetricKey(key); setSort({ key, dir: "desc" }); }}
              />
            </div>
          </div>

          {topLoading ? (
            <SkeletonCard rows={6} />
          ) : topError ? (
            <ErrorState message={topError} onRetry={refetchTop} />
          ) : sortedResearchers.length === 0 ? (
            <EmptyState icon={<Users />} title="No researcher data available yet." size="sm" />
          ) : (
            <Card padding="none">
              <DataTable
                columns={researcherColumns}
                rows={researcherRows}
                sortKey={sort.key}
                sortDir={sort.dir}
                onSort={({ key }) => handleSort(key)}
              />
              {sortedResearchers.length > 50 && (
                <div className="px-4 py-2 border-t border-slate-100 text-xs text-slate-400 text-center">
                  Showing top 50 of {fmtNum(sortedResearchers.length)} researchers
                </div>
              )}
            </Card>
          )}
        </section>

        {/* ══════════════════════════════════════════════════════════════
            SECTION 4: TOP INSTITUTIONS & COUNTRIES
        ══════════════════════════════════════════════════════════════ */}
        <section>
          <div className="text-xs font-semibold uppercase tracking-widest text-slate-500 mb-3">
            Top Institutions &amp; Countries
          </div>
          <div className="grid lg:grid-cols-2 gap-5">
            {/* Institutions */}
            <Card padding="none">
              <div className="flex items-center gap-2 px-4 py-3 border-b border-slate-100">
                <Building2 size={12} className="text-slate-400" />
                <span className="text-xs font-semibold uppercase tracking-widest text-slate-500">Top 20 Institutions</span>
              </div>
              {instLoading ? (
                <div className="p-4"><SkeletonCard rows={5} /></div>
              ) : instError ? (
                <div className="p-4"><ErrorState message={instError} onRetry={refetchInst} /></div>
              ) : topInstitutions.length === 0 ? (
                <EmptyState title="No institution data available." size="sm" />
              ) : (
                <DataTable columns={institutionColumns} rows={topInstitutions.slice(0, 20).map((i, idx) => ({ ...i, id: i.id || i.name || idx }))} />
              )}
            </Card>

            {/* Countries */}
            <Card padding="none">
              <div className="flex items-center gap-2 px-4 py-3 border-b border-slate-100">
                <Globe size={12} className="text-slate-400" />
                <span className="text-xs font-semibold uppercase tracking-widest text-slate-500">Top 20 Countries</span>
              </div>
              {countryLoading ? (
                <div className="p-4"><SkeletonCard rows={5} /></div>
              ) : countryError ? (
                <div className="p-4"><ErrorState message={countryError} onRetry={refetchCountries} /></div>
              ) : topCountries.length === 0 ? (
                <EmptyState title="No country data available." size="sm" />
              ) : (
                <DataTable columns={countryColumns} rows={topCountries.slice(0, 20).map((c, idx) => ({ ...c, id: c.country || idx }))} />
              )}
            </Card>
          </div>
        </section>

        {/* ══════════════════════════════════════════════════════════════
            SECTION 5: GROWTH TRENDS
        ══════════════════════════════════════════════════════════════ */}
        <section>
          <div className="text-xs font-semibold uppercase tracking-widest text-slate-500 mb-3">
            Monthly Avg SIS Growth
          </div>
          {trendLoading ? (
            <Card padding="lg"><Skeleton height="h-24" /></Card>
          ) : trendError ? (
            <ErrorState message={trendError} onRetry={refetchTrends} />
          ) : growthTrends.length === 0 ? (
            <EmptyState icon={<TrendingUp />} title="No growth trend data available yet." size="sm" />
          ) : (
            <Card padding="lg">
              <div className="flex items-center gap-2 mb-4">
                <TrendingUp size={12} style={{ color: TEAL }} />
                <span className="text-xs text-slate-500">Platform average SIS over time</span>
              </div>
              <BarChart
                data={growthTrends.map((t) => ({
                  label: t.month || t.period || "",
                  value: t.avg_sis || t.value || 0,
                }))}
                height={140}
                color={TEAL}
                showLabels
              />
              <div className="grid grid-cols-3 gap-4 mt-4 pt-4 border-t border-slate-100">
                {growthTrends.length >= 2 && (
                  <>
                    <div>
                      <div className="text-[10px] text-slate-400 uppercase tracking-wider mb-0.5">First Month</div>
                      <div className="text-sm font-semibold text-slate-800">
                        {fmtNum(growthTrends[0]?.avg_sis || growthTrends[0]?.value)}
                      </div>
                    </div>
                    <div>
                      <div className="text-[10px] text-slate-400 uppercase tracking-wider mb-0.5">Latest Month</div>
                      <div className="text-sm font-semibold" style={{ color: TEAL }}>
                        {fmtNum(growthTrends[growthTrends.length - 1]?.avg_sis || growthTrends[growthTrends.length - 1]?.value)}
                      </div>
                    </div>
                    <div>
                      <div className="text-[10px] text-slate-400 uppercase tracking-wider mb-0.5">Growth</div>
                      <div className="text-sm font-semibold" style={{ color: EMERALD }}>
                        {(() => {
                          const first = growthTrends[0]?.avg_sis || growthTrends[0]?.value || 0;
                          const last = growthTrends[growthTrends.length - 1]?.avg_sis || growthTrends[growthTrends.length - 1]?.value || 0;
                          if (!first) return "—";
                          const delta = Math.round(((last - first) / first) * 100);
                          return `${delta >= 0 ? "+" : ""}${delta}%`;
                        })()}
                      </div>
                    </div>
                  </>
                )}
              </div>
            </Card>
          )}
        </section>

        {/* ══════════════════════════════════════════════════════════════
            SECTION 6: RESEARCH AREAS
        ══════════════════════════════════════════════════════════════ */}
        <section>
          <div className="text-xs font-semibold uppercase tracking-widest text-slate-500 mb-3">
            Top Research Areas by Avg SIS
          </div>
          {areaLoading ? (
            <SkeletonCard rows={8} />
          ) : areaError ? (
            <ErrorState message={areaError} onRetry={refetchAreas} />
          ) : researchAreas.length === 0 ? (
            <EmptyState title="No research area data available yet." size="sm" />
          ) : (
            <Card padding="lg">
              <div className="space-y-3">
                {researchAreas.slice(0, 20).map((area, idx) => (
                  <div key={area.area || idx}>
                    <div className="flex items-center justify-between mb-1">
                      <div className="flex items-center gap-2">
                        <span className="text-[10px] text-slate-400 w-5 text-right">{idx + 1}.</span>
                        <span className="text-xs text-slate-700 truncate max-w-[220px]">{area.area || area.name}</span>
                      </div>
                      <div className="flex items-center gap-3">
                        {area.researcher_count != null && (
                          <span className="text-[10px] text-slate-400">{fmtNum(area.researcher_count)} researchers</span>
                        )}
                        <span className="text-xs font-semibold" style={{ color: TEAL }}>{fmtNum(area.avg_sis)}</span>
                      </div>
                    </div>
                    <div className="ml-7">
                      <MiniBar value={area.avg_sis || 0} max={maxAreaSIS} height={6} color={VIOLET} />
                    </div>
                  </div>
                ))}
              </div>
            </Card>
          )}
        </section>

        {/* Footer note */}
        <div className="text-[10px] text-slate-400 text-center pb-4">
          Impact scores are computed from publication, citation, collaboration, teaching, and grant data.
          Scores refresh periodically or on demand via "Refresh All Impact Scores."
        </div>

      </div>
    </AdministrationLayout>
  );
}
