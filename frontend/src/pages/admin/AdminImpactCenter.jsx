import { useState, useEffect, useCallback } from "react";
import api from "@/lib/api";
import { NAVY } from "@/lib/tokens";
import { AdministrationLayout } from "@/layouts";
import {
  RefreshCw, Users, Award, BookOpen, BarChart2,
  Globe, Building2, TrendingUp, AlertCircle,
  ChevronUp, ChevronDown, Activity,
} from "lucide-react";

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
  "#94A3B8", "#64748B", "#0891B2", "#0F2847",
  "#7C3AED", "#D97706", "#D97706",
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

// ── Skeleton ──────────────────────────────────────────────────────────────────

function Skeleton({ h = "h-4", w = "w-full" }) {
  return <div className={`${h} ${w} bg-[#1a3050] animate-pulse rounded-sm`} />;
}

function SkeletonCard({ rows = 3 }) {
  return (
    <div className="border border-[#1a3050] bg-[#0B1C35] p-4 animate-pulse space-y-3">
      <Skeleton h="h-3" w="w-1/3" />
      <Skeleton h="h-7" w="w-1/2" />
      {Array.from({ length: rows - 2 }).map((_, i) => <Skeleton key={i} />)}
    </div>
  );
}

// ── Error card ────────────────────────────────────────────────────────────────

function ErrorCard({ message, onRetry }) {
  return (
    <div className="border border-red-800 bg-red-950/30 p-4 text-center">
      <AlertCircle size={20} strokeWidth={1.5} className="text-red-400 mx-auto mb-2" />
      <p className="text-red-400 text-sm mb-2">{message || "Failed to load."}</p>
      {onRetry && (
        <button onClick={onRetry} className="text-xs border border-red-700 text-red-400 px-3 py-1 hover:bg-red-950 transition-colors">
          Retry
        </button>
      )}
    </div>
  );
}

// ── KPI Card ──────────────────────────────────────────────────────────────────

function KpiCard({ label, value, sub, icon: Icon, loading, highlight }) {
  return (
    <div className={`border bg-[#0B1C35] p-5 ${highlight ? "border-[#0891B2]" : "border-[#1a3050]"}`}>
      <div className="flex items-center justify-between mb-2">
        <div className="text-[9px] font-semibold uppercase tracking-widest text-slate-500">{label}</div>
        {Icon && <Icon size={13} strokeWidth={1.5} className="text-slate-600" />}
      </div>
      {loading ? (
        <Skeleton h="h-8" w="w-2/3" />
      ) : (
        <>
          <div className={`font-serif text-3xl ${highlight ? "text-[#0891B2]" : "text-white"}`}>{value}</div>
          {sub && <div className="text-[10px] text-slate-500 mt-1">{sub}</div>}
        </>
      )}
    </div>
  );
}

// ── Horizontal Bar ────────────────────────────────────────────────────────────

function HBar({ label, value, maxVal, color = "#0F2847", sub }) {
  const w = pct(value || 0, maxVal || 1);
  return (
    <div>
      <div className="flex items-center justify-between mb-1">
        <span className="text-xs text-slate-400 truncate max-w-[65%]">{label}</span>
        <span className="text-xs text-slate-300 font-medium">{fmtNum(value)}</span>
      </div>
      <div className="h-2 bg-[#1a3050] w-full overflow-hidden">
        <div className="h-full transition-all duration-700" style={{ width: `${w}%`, backgroundColor: color }} />
      </div>
      {sub && <div className="text-[9px] text-slate-600 mt-0.5">{sub}</div>}
    </div>
  );
}

// ── Vertical Bar Chart (div-based) ────────────────────────────────────────────

function VBarChart({ items = [], valueKey = "value", labelKey = "label", color = "#0891B2", height = 100 }) {
  const max = Math.max(...items.map((i) => i[valueKey] || 0), 1);
  return (
    <div className="flex items-end gap-1" style={{ height }}>
      {items.map((item, idx) => {
        const h = Math.max(4, pct(item[valueKey] || 0, max));
        return (
          <div key={idx} className="flex-1 flex flex-col items-center gap-1">
            <div
              className="w-full transition-all duration-700 min-h-[4px]"
              style={{ height: `${h}%`, backgroundColor: color }}
              title={`${item[labelKey]}: ${item[valueKey]}`}
            />
            <div className="text-[8px] text-slate-600 truncate w-full text-center">{item[labelKey]}</div>
          </div>
        );
      })}
    </div>
  );
}

// ── Sortable table header ─────────────────────────────────────────────────────

function SortHeader({ label, sortKey, sortState, onSort }) {
  const { key, dir } = sortState;
  const active = key === sortKey;
  return (
    <button
      onClick={() => onSort(sortKey)}
      className="flex items-center gap-1 text-[9px] font-semibold uppercase tracking-widest text-slate-500 hover:text-slate-300 transition-colors"
    >
      {label}
      {active ? (
        dir === "asc" ? <ChevronUp size={10} /> : <ChevronDown size={10} />
      ) : (
        <ChevronDown size={10} className="opacity-30" />
      )}
    </button>
  );
}

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

  return (
    <AdministrationLayout
      title="Research Impact Center"
      subtitle="Platform-wide Synaptiq Impact Score analytics"
      actions={
        <div className="flex items-center gap-3">
          {refreshMsg && (
            <span className="text-xs text-[#0891B2] animate-pulse">{refreshMsg}</span>
          )}
          <button
            onClick={handleRefreshAll}
            disabled={refreshingAll}
            className="inline-flex items-center gap-2 bg-[#0891B2] text-white px-4 py-2 text-xs hover:bg-[#0e7490] disabled:opacity-50 transition-colors"
          >
            <RefreshCw size={12} strokeWidth={1.5} className={refreshingAll ? "animate-spin" : ""} />
            {refreshingAll ? "Triggering…" : "Refresh All Impact Scores"}
          </button>
        </div>
      }
    >
      <div className="space-y-10">

        {/* ══════════════════════════════════════════════════════════════
            SECTION 1: PLATFORM KPIs
        ══════════════════════════════════════════════════════════════ */}
        <section>
          <div className="text-[9px] font-semibold uppercase tracking-widest text-slate-500 mb-4">
            Platform Overview
          </div>
          {statsError ? (
            <ErrorCard message={statsError} onRetry={refetchStats} />
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
          <div className="text-[9px] font-semibold uppercase tracking-widest text-slate-500 mb-4">
            SIS Distribution by Level
          </div>
          {statsLoading ? (
            <div className="border border-[#1a3050] bg-[#0B1C35] p-5 space-y-3">
              {Array.from({ length: 7 }).map((_, i) => <Skeleton key={i} />)}
            </div>
          ) : statsError ? (
            <ErrorCard message={statsError} onRetry={refetchStats} />
          ) : (
            <div className="border border-[#1a3050] bg-[#0B1C35] p-5 space-y-3">
              {SIS_BUCKETS.map((bucket, idx) => {
                const count = distribution[bucket.key] || distribution[bucket.label] || 0;
                return (
                  <HBar
                    key={bucket.key}
                    label={`${bucket.label} (${bucket.range})`}
                    value={count}
                    maxVal={maxBucketCount}
                    color={BUCKET_COLORS[idx]}
                    sub={`${fmtNum(count)} researchers`}
                  />
                );
              })}
            </div>
          )}
        </section>

        {/* ══════════════════════════════════════════════════════════════
            SECTION 3: TOP RESEARCHERS TABLE
        ══════════════════════════════════════════════════════════════ */}
        <section>
          <div className="flex items-center justify-between mb-4 flex-wrap gap-3">
            <div className="text-[9px] font-semibold uppercase tracking-widest text-slate-500">
              Top Researchers
            </div>
            <div className="flex items-center gap-2">
              <span className="text-xs text-slate-500">Sort by:</span>
              {METRIC_OPTIONS.map((opt) => (
                <button
                  key={opt.key}
                  onClick={() => { setMetricKey(opt.key); setSort({ key: opt.key, dir: "desc" }); }}
                  className={`text-xs px-3 py-1 border transition-colors ${
                    metricKey === opt.key
                      ? "border-[#0891B2] bg-[#0891B2]/10 text-[#0891B2]"
                      : "border-[#1a3050] text-slate-500 hover:border-slate-500 hover:text-slate-300"
                  }`}
                >
                  {opt.label}
                </button>
              ))}
            </div>
          </div>

          {topLoading ? (
            <div className="border border-[#1a3050] bg-[#0B1C35] overflow-hidden">
              {Array.from({ length: 10 }).map((_, i) => (
                <div key={i} className="flex gap-4 p-3 border-b border-[#1a3050] animate-pulse">
                  <Skeleton h="h-3" w="w-6" />
                  <Skeleton h="h-3" w="w-1/3" />
                  <Skeleton h="h-3" w="w-1/4" />
                  <Skeleton h="h-3" w="w-1/6" />
                </div>
              ))}
            </div>
          ) : topError ? (
            <ErrorCard message={topError} onRetry={refetchTop} />
          ) : sortedResearchers.length === 0 ? (
            <div className="border border-dashed border-[#1a3050] p-8 text-center text-slate-600 text-sm">
              No researcher data available yet.
            </div>
          ) : (
            <div className="border border-[#1a3050] bg-[#0B1C35] overflow-hidden">
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-[#1a3050] bg-[#060F1E]">
                      <th className="text-left px-4 py-3">
                        <span className="text-[9px] font-semibold uppercase tracking-widest text-slate-500">#</span>
                      </th>
                      <th className="text-left px-4 py-3">
                        <span className="text-[9px] font-semibold uppercase tracking-widest text-slate-500">Researcher</span>
                      </th>
                      <th className="text-left px-4 py-3">
                        <span className="text-[9px] font-semibold uppercase tracking-widest text-slate-500">Institution</span>
                      </th>
                      <th className="text-left px-4 py-3">
                        <span className="text-[9px] font-semibold uppercase tracking-widest text-slate-500">Country</span>
                      </th>
                      <th className="text-left px-4 py-3">
                        <SortHeader label="SIS Score" sortKey="sis_score" sortState={sort} onSort={handleSort} />
                      </th>
                      <th className="text-left px-4 py-3">
                        <SortHeader label="H-Index" sortKey="h_index" sortState={sort} onSort={handleSort} />
                      </th>
                      <th className="text-left px-4 py-3">
                        <SortHeader label="Publications" sortKey="publications" sortState={sort} onSort={handleSort} />
                      </th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-[#1a3050]">
                    {sortedResearchers.slice(0, 50).map((r, idx) => (
                      <tr key={r.id || idx} className="hover:bg-[#0F2847]/40 transition-colors">
                        <td className="px-4 py-3 text-slate-500 text-xs">{idx + 1}</td>
                        <td className="px-4 py-3">
                          <div className="font-medium text-white text-xs">{fmt(r.full_name || r.name)}</div>
                          {r.role && <div className="text-[10px] text-slate-500 mt-0.5">{r.role}</div>}
                        </td>
                        <td className="px-4 py-3 text-xs text-slate-400 max-w-[180px] truncate">
                          {fmt(r.institution)}
                        </td>
                        <td className="px-4 py-3 text-xs text-slate-400">{fmt(r.country)}</td>
                        <td className="px-4 py-3">
                          <span className="font-semibold text-[#0891B2]">{fmtNum(r.sis_score)}</span>
                        </td>
                        <td className="px-4 py-3 text-xs text-slate-300">{fmt(r.h_index)}</td>
                        <td className="px-4 py-3 text-xs text-slate-300">{fmtNum(r.publications)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              {sortedResearchers.length > 50 && (
                <div className="px-4 py-2 border-t border-[#1a3050] text-xs text-slate-500 text-center">
                  Showing top 50 of {fmtNum(sortedResearchers.length)} researchers
                </div>
              )}
            </div>
          )}
        </section>

        {/* ══════════════════════════════════════════════════════════════
            SECTION 4: TOP INSTITUTIONS & COUNTRIES
        ══════════════════════════════════════════════════════════════ */}
        <section>
          <div className="text-[9px] font-semibold uppercase tracking-widest text-slate-500 mb-4">
            Top Institutions &amp; Countries
          </div>
          <div className="grid lg:grid-cols-2 gap-5">
            {/* Institutions */}
            <div className="border border-[#1a3050] bg-[#0B1C35] overflow-hidden">
              <div className="flex items-center gap-2 px-4 py-3 border-b border-[#1a3050] bg-[#060F1E]">
                <Building2 size={12} strokeWidth={1.5} className="text-slate-500" />
                <span className="text-[9px] font-semibold uppercase tracking-widest text-slate-500">Top 20 Institutions</span>
              </div>
              {instLoading ? (
                <div className="p-4 space-y-3">{Array.from({ length: 5 }).map((_, i) => <Skeleton key={i} />)}</div>
              ) : instError ? (
                <div className="p-4"><ErrorCard message={instError} onRetry={refetchInst} /></div>
              ) : topInstitutions.length === 0 ? (
                <div className="p-6 text-center text-slate-600 text-xs">No institution data available.</div>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-xs">
                    <thead>
                      <tr className="border-b border-[#1a3050]">
                        <th className="text-left px-3 py-2 text-[8px] font-semibold uppercase tracking-wider text-slate-600">Institution</th>
                        <th className="text-left px-3 py-2 text-[8px] font-semibold uppercase tracking-wider text-slate-600">Researchers</th>
                        <th className="text-left px-3 py-2 text-[8px] font-semibold uppercase tracking-wider text-slate-600">Avg SIS</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-[#1a3050]">
                      {topInstitutions.slice(0, 20).map((inst, idx) => (
                        <tr key={inst.id || inst.name || idx} className="hover:bg-[#0F2847]/30 transition-colors">
                          <td className="px-3 py-2">
                            <div className="text-slate-300 truncate max-w-[180px]">{fmt(inst.name)}</div>
                            {inst.country && <div className="text-slate-600 text-[9px]">{inst.country}</div>}
                          </td>
                          <td className="px-3 py-2 text-slate-400">{fmtNum(inst.researcher_count || inst.researchers)}</td>
                          <td className="px-3 py-2">
                            <div className="flex items-center gap-2">
                              <span className="text-[#0891B2] font-semibold">{fmtNum(inst.avg_sis)}</span>
                              <div className="flex-1 h-1 bg-[#1a3050] min-w-[40px]">
                                <div
                                  className="h-full bg-[#0891B2]/40 transition-all duration-700"
                                  style={{ width: `${pct(inst.avg_sis || 0, maxInstSIS)}%` }}
                                />
                              </div>
                            </div>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>

            {/* Countries */}
            <div className="border border-[#1a3050] bg-[#0B1C35] overflow-hidden">
              <div className="flex items-center gap-2 px-4 py-3 border-b border-[#1a3050] bg-[#060F1E]">
                <Globe size={12} strokeWidth={1.5} className="text-slate-500" />
                <span className="text-[9px] font-semibold uppercase tracking-widest text-slate-500">Top 20 Countries</span>
              </div>
              {countryLoading ? (
                <div className="p-4 space-y-3">{Array.from({ length: 5 }).map((_, i) => <Skeleton key={i} />)}</div>
              ) : countryError ? (
                <div className="p-4"><ErrorCard message={countryError} onRetry={refetchCountries} /></div>
              ) : topCountries.length === 0 ? (
                <div className="p-6 text-center text-slate-600 text-xs">No country data available.</div>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-xs">
                    <thead>
                      <tr className="border-b border-[#1a3050]">
                        <th className="text-left px-3 py-2 text-[8px] font-semibold uppercase tracking-wider text-slate-600">Country</th>
                        <th className="text-left px-3 py-2 text-[8px] font-semibold uppercase tracking-wider text-slate-600">Researchers</th>
                        <th className="text-left px-3 py-2 text-[8px] font-semibold uppercase tracking-wider text-slate-600">Avg SIS</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-[#1a3050]">
                      {topCountries.slice(0, 20).map((c, idx) => (
                        <tr key={c.country || idx} className="hover:bg-[#0F2847]/30 transition-colors">
                          <td className="px-3 py-2 text-slate-300">{fmt(c.country)}</td>
                          <td className="px-3 py-2 text-slate-400">{fmtNum(c.researcher_count || c.researchers)}</td>
                          <td className="px-3 py-2">
                            <div className="flex items-center gap-2">
                              <span className="text-[#0891B2] font-semibold">{fmtNum(c.avg_sis)}</span>
                              <div className="flex-1 h-1 bg-[#1a3050] min-w-[40px]">
                                <div
                                  className="h-full bg-[#0891B2]/40 transition-all duration-700"
                                  style={{ width: `${pct(c.avg_sis || 0, maxCountrySIS)}%` }}
                                />
                              </div>
                            </div>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          </div>
        </section>

        {/* ══════════════════════════════════════════════════════════════
            SECTION 5: GROWTH TRENDS
        ══════════════════════════════════════════════════════════════ */}
        <section>
          <div className="text-[9px] font-semibold uppercase tracking-widest text-slate-500 mb-4">
            Monthly Avg SIS Growth
          </div>
          {trendLoading ? (
            <div className="border border-[#1a3050] bg-[#0B1C35] p-5">
              <Skeleton h="h-24" />
            </div>
          ) : trendError ? (
            <ErrorCard message={trendError} onRetry={refetchTrends} />
          ) : growthTrends.length === 0 ? (
            <div className="border border-dashed border-[#1a3050] p-8 text-center text-slate-600 text-sm">
              No growth trend data available yet.
            </div>
          ) : (
            <div className="border border-[#1a3050] bg-[#0B1C35] p-5">
              <div className="flex items-center gap-2 mb-4">
                <TrendingUp size={12} strokeWidth={1.5} className="text-[#0891B2]" />
                <span className="text-xs text-slate-400">Platform average SIS over time</span>
              </div>
              <VBarChart
                items={growthTrends.map((t) => ({
                  label: t.month || t.period || "",
                  value: t.avg_sis || t.value || 0,
                }))}
                height={140}
                color="#0891B2"
              />
              <div className="grid grid-cols-3 gap-4 mt-4 pt-4 border-t border-[#1a3050]">
                {growthTrends.length >= 2 && (
                  <>
                    <div>
                      <div className="text-[9px] text-slate-500 uppercase tracking-wider mb-0.5">First Month</div>
                      <div className="text-sm font-semibold text-white">
                        {fmtNum(growthTrends[0]?.avg_sis || growthTrends[0]?.value)}
                      </div>
                    </div>
                    <div>
                      <div className="text-[9px] text-slate-500 uppercase tracking-wider mb-0.5">Latest Month</div>
                      <div className="text-sm font-semibold text-[#0891B2]">
                        {fmtNum(growthTrends[growthTrends.length - 1]?.avg_sis || growthTrends[growthTrends.length - 1]?.value)}
                      </div>
                    </div>
                    <div>
                      <div className="text-[9px] text-slate-500 uppercase tracking-wider mb-0.5">Growth</div>
                      <div className="text-sm font-semibold text-emerald-400">
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
            </div>
          )}
        </section>

        {/* ══════════════════════════════════════════════════════════════
            SECTION 6: RESEARCH AREAS
        ══════════════════════════════════════════════════════════════ */}
        <section>
          <div className="text-[9px] font-semibold uppercase tracking-widest text-slate-500 mb-4">
            Top Research Areas by Avg SIS
          </div>
          {areaLoading ? (
            <div className="border border-[#1a3050] bg-[#0B1C35] p-5 space-y-3">
              {Array.from({ length: 8 }).map((_, i) => <Skeleton key={i} />)}
            </div>
          ) : areaError ? (
            <ErrorCard message={areaError} onRetry={refetchAreas} />
          ) : researchAreas.length === 0 ? (
            <div className="border border-dashed border-[#1a3050] p-8 text-center text-slate-600 text-sm">
              No research area data available yet.
            </div>
          ) : (
            <div className="border border-[#1a3050] bg-[#0B1C35] p-5 space-y-3">
              {researchAreas.slice(0, 20).map((area, idx) => (
                <div key={area.area || idx}>
                  <div className="flex items-center justify-between mb-1">
                    <div className="flex items-center gap-2">
                      <span className="text-[9px] text-slate-600 w-5 text-right">{idx + 1}.</span>
                      <span className="text-xs text-slate-300 truncate max-w-[220px]">{area.area || area.name}</span>
                    </div>
                    <div className="flex items-center gap-3">
                      {area.researcher_count != null && (
                        <span className="text-[9px] text-slate-600">{fmtNum(area.researcher_count)} researchers</span>
                      )}
                      <span className="text-xs font-semibold text-[#0891B2]">{fmtNum(area.avg_sis)}</span>
                    </div>
                  </div>
                  <div className="h-1.5 bg-[#1a3050] w-full overflow-hidden ml-7">
                    <div
                      className="h-full transition-all duration-700"
                      style={{ width: `${pct(area.avg_sis || 0, maxAreaSIS)}%`, backgroundColor: "#7C3AED" }}
                    />
                  </div>
                </div>
              ))}
            </div>
          )}
        </section>

        {/* Footer note */}
        <div className="text-[10px] text-slate-600 text-center pb-4">
          Impact scores are computed from publication, citation, collaboration, teaching, and grant data.
          Scores refresh periodically or on demand via "Refresh All Impact Scores."
        </div>

      </div>
    </AdministrationLayout>
  );
}
