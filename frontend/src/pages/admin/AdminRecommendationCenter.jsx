import { useState, useEffect, useCallback } from "react";
import api from "@/lib/api";
import { toast } from "sonner";
import { NAVY } from "@/lib/tokens";
import {
  Activity, Users, ThumbsUp, XCircle, Percent,
  RefreshCw, AlertCircle, ChevronLeft, ChevronRight,
} from "lucide-react";
import { AdministrationLayout } from "@/layouts";

// ── Helpers ───────────────────────────────────────────────────────────────────

function fmt(val, fallback = "—") {
  if (val == null) return fallback;
  return val;
}

function fmtPct(val, fallback = "—") {
  if (val == null) return fallback;
  return `${Math.round(val * 100) / 100}%`;
}

function formatDate(iso) {
  if (!iso) return "—";
  try {
    return new Date(iso).toLocaleDateString("en-US", {
      month: "short", day: "numeric", year: "numeric",
      hour: "2-digit", minute: "2-digit",
    });
  } catch {
    return iso;
  }
}

function SkeletonBlock({ className = "" }) {
  return <div className={`animate-pulse bg-slate-200 rounded ${className}`} />;
}

function ErrorCard({ message, onRetry }) {
  return (
    <div className="border border-red-200 bg-red-50 p-6 text-center rounded">
      <AlertCircle size={24} strokeWidth={1.5} className="text-red-400 mx-auto mb-2" />
      <p className="text-red-700 text-sm mb-3">{message || "Failed to load data."}</p>
      {onRetry && (
        <button
          onClick={onRetry}
          className="text-xs border border-red-300 text-red-700 px-3 py-1.5 hover:bg-red-100 transition-colors"
        >
          Retry
        </button>
      )}
    </div>
  );
}

// ── Metric card ───────────────────────────────────────────────────────────────

function MetricCard({ icon: Icon, label, value, sub, loading, color = "blue" }) {
  const palette = {
    blue:  { bg: "bg-blue-50",   text: "text-blue-700",   icon: "text-blue-400" },
    green: { bg: "bg-emerald-50", text: "text-emerald-700", icon: "text-emerald-400" },
    amber: { bg: "bg-amber-50",  text: "text-amber-700",  icon: "text-amber-400" },
    red:   { bg: "bg-red-50",    text: "text-red-700",    icon: "text-red-400" },
  };
  const c = palette[color] || palette.blue;

  return (
    <div className="border border-slate-200 bg-white p-5">
      <div className="flex items-start justify-between gap-3 mb-3">
        <div className="text-xs font-medium text-slate-500 uppercase tracking-widest">{label}</div>
        <div className={`w-8 h-8 ${c.bg} flex items-center justify-center`}>
          <Icon size={15} strokeWidth={1.5} className={c.icon} />
        </div>
      </div>
      {loading ? (
        <SkeletonBlock className="h-8 w-24 mb-1" />
      ) : (
        <div className={`text-3xl font-bold font-mono ${c.text}`}>{value}</div>
      )}
      {sub && !loading && (
        <div className="text-xs text-slate-400 mt-1">{sub}</div>
      )}
    </div>
  );
}

// ── Horizontal bar chart (div-based) ─────────────────────────────────────────

const TYPE_COLORS = {
  researchers: "bg-blue-500",
  projects:    "bg-indigo-500",
  journals:    "bg-violet-500",
  conferences: "bg-amber-500",
  grants:      "bg-emerald-500",
  mentors:     "bg-teal-500",
  reviewers:   "bg-rose-500",
};

const ACTION_COLORS = {
  accepted:   "bg-emerald-500",
  bookmarked: "bg-blue-400",
  dismissed:  "bg-red-400",
  clicked:    "bg-slate-400",
};

function InteractionsByTypeChart({ data, loading }) {
  if (loading) {
    return (
      <div className="space-y-3">
        {Array.from({ length: 7 }).map((_, i) => (
          <div key={i} className="flex items-center gap-3">
            <SkeletonBlock className="w-28 h-4" />
            <SkeletonBlock className="flex-1 h-5" />
            <SkeletonBlock className="w-10 h-4" />
          </div>
        ))}
      </div>
    );
  }
  if (!data || data.length === 0) {
    return <p className="text-slate-400 text-sm text-center py-6">No interaction data yet.</p>;
  }

  const maxTotal = Math.max(...data.map((d) => (d.total || 0)), 1);

  return (
    <div className="space-y-3">
      {/* Legend */}
      <div className="flex items-center gap-4 flex-wrap mb-2">
        {Object.entries(ACTION_COLORS).map(([action, color]) => (
          <div key={action} className="flex items-center gap-1.5 text-xs text-slate-500">
            <div className={`w-3 h-3 rounded-sm ${color}`} />
            <span className="capitalize">{action}</span>
          </div>
        ))}
      </div>
      {data.map((d) => {
        const total = d.total || 0;
        const accepted   = d.accepted   || 0;
        const bookmarked = d.bookmarked || 0;
        const dismissed  = d.dismissed  || 0;
        const clicked    = d.clicked    || 0;
        const barWidth   = total === 0 ? 0 : Math.round((total / maxTotal) * 100);
        // sub-widths as % of total bar
        const acceptedW   = total === 0 ? 0 : Math.round((accepted   / total) * 100);
        const bookmarkedW = total === 0 ? 0 : Math.round((bookmarked / total) * 100);
        const dismissedW  = total === 0 ? 0 : Math.round((dismissed  / total) * 100);
        const clickedW    = 100 - acceptedW - bookmarkedW - dismissedW;

        return (
          <div key={d.type} className="flex items-center gap-3">
            <div className="w-28 text-xs text-slate-600 font-medium capitalize flex-shrink-0 truncate">
              {d.type}
            </div>
            <div className="flex-1 h-5 bg-slate-100 overflow-hidden">
              <div
                className="h-full flex transition-all duration-700"
                style={{ width: `${barWidth}%` }}
              >
                {acceptedW   > 0 && <div className={`h-full ${ACTION_COLORS.accepted}`}   style={{ width: `${acceptedW}%` }} />}
                {bookmarkedW > 0 && <div className={`h-full ${ACTION_COLORS.bookmarked}`} style={{ width: `${bookmarkedW}%` }} />}
                {clickedW    > 0 && <div className={`h-full ${ACTION_COLORS.clicked}`}    style={{ width: `${Math.max(clickedW, 0)}%` }} />}
                {dismissedW  > 0 && <div className={`h-full ${ACTION_COLORS.dismissed}`}  style={{ width: `${dismissedW}%` }} />}
              </div>
            </div>
            <div className="w-10 text-right text-xs font-mono text-slate-600 flex-shrink-0">
              {total.toLocaleString()}
            </div>
          </div>
        );
      })}
    </div>
  );
}

function AcceptanceByTypeChart({ data, loading }) {
  if (loading) {
    return (
      <div className="space-y-3">
        {Array.from({ length: 7 }).map((_, i) => (
          <div key={i} className="flex items-center gap-3">
            <SkeletonBlock className="w-28 h-4" />
            <SkeletonBlock className="flex-1 h-4" />
            <SkeletonBlock className="w-10 h-4" />
          </div>
        ))}
      </div>
    );
  }
  if (!data || data.length === 0) {
    return <p className="text-slate-400 text-sm text-center py-6">No acceptance data yet.</p>;
  }

  return (
    <div className="space-y-3">
      {data.map((d) => {
        const rate = Math.round((d.acceptance_rate || 0) * 100) / 100;
        const color = TYPE_COLORS[d.type] || "bg-slate-400";
        return (
          <div key={d.type} className="flex items-center gap-3">
            <div className="w-28 text-xs text-slate-600 font-medium capitalize flex-shrink-0 truncate">
              {d.type}
            </div>
            <div className="flex-1 h-4 bg-slate-100 overflow-hidden">
              <div
                className={`h-full ${color} transition-all duration-700`}
                style={{ width: `${Math.min(rate, 100)}%` }}
              />
            </div>
            <div className="w-12 text-right text-xs font-mono text-slate-600 flex-shrink-0">
              {rate.toFixed(1)}%
            </div>
          </div>
        );
      })}
    </div>
  );
}

function TopAreasChart({ data, loading }) {
  if (loading) {
    return (
      <div className="space-y-3">
        {Array.from({ length: 10 }).map((_, i) => (
          <div key={i} className="flex items-center gap-3">
            <SkeletonBlock className="w-36 h-4" />
            <SkeletonBlock className="flex-1 h-4" />
            <SkeletonBlock className="w-10 h-4" />
          </div>
        ))}
      </div>
    );
  }
  if (!data || data.length === 0) {
    return <p className="text-slate-400 text-sm text-center py-6">No area data yet.</p>;
  }

  const maxCount = Math.max(...data.map((d) => d.count || 0), 1);

  return (
    <div className="space-y-2.5">
      {data.slice(0, 10).map((d, i) => {
        const pct = Math.round(((d.count || 0) / maxCount) * 100);
        const colors = [
          "bg-blue-500", "bg-indigo-500", "bg-violet-500", "bg-emerald-500",
          "bg-teal-500", "bg-amber-500", "bg-rose-500", "bg-cyan-500", "bg-slate-500", "bg-purple-500",
        ];
        return (
          <div key={d.area || d.name || i} className="flex items-center gap-3">
            <div className="w-36 text-xs text-slate-600 flex-shrink-0 truncate">
              {d.area || d.name || "Unknown"}
            </div>
            <div className="flex-1 h-4 bg-slate-100 overflow-hidden">
              <div
                className={`h-full ${colors[i % colors.length]} transition-all duration-700`}
                style={{ width: `${pct}%` }}
              />
            </div>
            <div className="w-10 text-right text-xs font-mono text-slate-600 flex-shrink-0">
              {(d.count || 0).toLocaleString()}
            </div>
          </div>
        );
      })}
    </div>
  );
}

// ── Quality metric badge ──────────────────────────────────────────────────────

function QualityBadge({ label, value, color }) {
  const palette = {
    green: "bg-emerald-50 text-emerald-700 border-emerald-200",
    blue:  "bg-blue-50 text-blue-700 border-blue-200",
    amber: "bg-amber-50 text-amber-700 border-amber-200",
    slate: "bg-slate-100 text-slate-600 border-slate-200",
  };
  return (
    <div className="border border-slate-200 bg-white p-3">
      <div className="text-xs text-slate-500 mb-1">{label}</div>
      <div className={`inline-flex items-center px-2 py-1 text-sm font-bold border ${palette[color] || palette.slate}`}>
        {value}
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// ── MAIN COMPONENT ────────────────────────────────────────────────────────────
// ─────────────────────────────────────────────────────────────────────────────

const PAGE_SIZE = 20;

export default function AdminRecommendationCenter() {
  // ── State ────────────────────────────────────────────────────────────────────

  const [stats,          setStats]          = useState(null);
  const [statsError,     setStatsError]     = useState(null);
  const [statsLoading,   setStatsLoading]   = useState(true);

  const [byType,         setByType]         = useState([]);
  const [byTypeLoading,  setByTypeLoading]  = useState(true);
  const [byTypeError,    setByTypeError]    = useState(null);

  const [coverage,       setCoverage]       = useState(null);
  const [coverageLoading,setCoverageLoading]= useState(true);
  const [coverageError,  setCoverageError]  = useState(null);

  const [topAreas,       setTopAreas]       = useState([]);
  const [topAreasLoading,setTopAreasLoading]= useState(true);
  const [topAreasError,  setTopAreasError]  = useState(null);

  const [interactions,   setInteractions]   = useState([]);
  const [intLoading,     setIntLoading]     = useState(true);
  const [intError,       setIntError]       = useState(null);
  const [intPage,        setIntPage]        = useState(1);
  const [intTotal,       setIntTotal]       = useState(0);

  const [quality,        setQuality]        = useState(null);
  const [qualityLoading, setQualityLoading] = useState(true);
  const [qualityError,   setQualityError]   = useState(null);

  const [refreshingAll,  setRefreshingAll]  = useState(false);

  // ── Fetchers ─────────────────────────────────────────────────────────────────

  const fetchStats = useCallback(async () => {
    setStatsLoading(true);
    setStatsError(null);
    try {
      const res = await api.get("/admin/recommendations/stats");
      setStats(res.data);
    } catch (err) {
      setStatsError(err?.response?.data?.detail || "Failed to load stats.");
    } finally {
      setStatsLoading(false);
    }
  }, []);

  const fetchByType = useCallback(async () => {
    setByTypeLoading(true);
    setByTypeError(null);
    try {
      const res = await api.get("/admin/recommendations/stats");
      // by_type may be in the same stats response, or a separate key
      const d = res.data;
      const arr = d.by_type || d.interactions_by_type || [];
      setByType(Array.isArray(arr) ? arr : []);
    } catch (err) {
      setByTypeError(err?.response?.data?.detail || "Failed to load type breakdown.");
    } finally {
      setByTypeLoading(false);
    }
  }, []);

  const fetchCoverage = useCallback(async () => {
    setCoverageLoading(true);
    setCoverageError(null);
    try {
      const res = await api.get("/admin/recommendations/profile-coverage");
      setCoverage(res.data);
    } catch (err) {
      setCoverageError(err?.response?.data?.detail || "Failed to load coverage data.");
    } finally {
      setCoverageLoading(false);
    }
  }, []);

  const fetchTopAreas = useCallback(async () => {
    setTopAreasLoading(true);
    setTopAreasError(null);
    try {
      const res = await api.get("/admin/recommendations/top-areas");
      const arr = res.data?.areas || res.data?.top_areas || res.data || [];
      setTopAreas(Array.isArray(arr) ? arr : []);
    } catch (err) {
      setTopAreasError(err?.response?.data?.detail || "Failed to load top areas.");
    } finally {
      setTopAreasLoading(false);
    }
  }, []);

  const fetchInteractions = useCallback(async (page = 1) => {
    setIntLoading(true);
    setIntError(null);
    try {
      const res = await api.get("/admin/recommendations/interactions", {
        params: { page, page_size: PAGE_SIZE },
      });
      const d = res.data;
      const arr = d.interactions || d.data || d || [];
      setInteractions(Array.isArray(arr) ? arr : []);
      setIntTotal(d.total || arr.length || 0);
    } catch (err) {
      setIntError(err?.response?.data?.detail || "Failed to load interactions.");
    } finally {
      setIntLoading(false);
    }
  }, []);

  const fetchQuality = useCallback(async () => {
    setQualityLoading(true);
    setQualityError(null);
    try {
      const res = await api.get("/admin/recommendations/quality-metrics");
      setQuality(res.data);
    } catch (err) {
      setQualityError(err?.response?.data?.detail || "Failed to load quality metrics.");
    } finally {
      setQualityLoading(false);
    }
  }, []);

  // Mount: fetch all
  useEffect(() => {
    fetchStats();
    fetchByType();
    fetchCoverage();
    fetchTopAreas();
    fetchInteractions(1);
    fetchQuality();
  }, [fetchStats, fetchByType, fetchCoverage, fetchTopAreas, fetchInteractions, fetchQuality]);

  // Refresh interactions on page change
  useEffect(() => {
    fetchInteractions(intPage);
  }, [intPage, fetchInteractions]);

  // ── Derived metrics ───────────────────────────────────────────────────────────

  const totalInteractions = stats?.total_interactions ?? null;
  const totalAccepted     = stats?.total_accepted     ?? null;
  const totalDismissals   = stats?.total_dismissals   ?? null;

  const acceptanceRate =
    totalInteractions && totalAccepted
      ? ((totalAccepted / totalInteractions) * 100).toFixed(1)
      : null;

  const dismissalRate =
    totalInteractions && totalDismissals
      ? ((totalDismissals / totalInteractions) * 100).toFixed(1)
      : null;

  const coveragePct = coverage?.coverage_pct ?? coverage?.pct ?? null;

  // ── Refresh all profiles ──────────────────────────────────────────────────────

  const handleRefreshAll = async () => {
    if (refreshingAll) return;
    setRefreshingAll(true);
    try {
      const res = await api.post("/admin/recommendations/refresh-all");
      const count = res.data?.profile_count || res.data?.count || "all";
      toast.success(`Refreshing ${count} profiles…`);
      // Re-fetch coverage after a short delay
      setTimeout(() => {
        fetchCoverage();
        setRefreshingAll(false);
      }, 3000);
    } catch (err) {
      toast.error(err?.response?.data?.detail || "Failed to trigger profile refresh.");
      setRefreshingAll(false);
    }
  };

  // ── Quality metrics helpers ────────────────────────────────────────────────────

  const qualityItems = quality
    ? [
        ...(quality.avg_score_by_type
          ? Object.entries(quality.avg_score_by_type).map(([type, score]) => ({
              label: `Avg Match: ${type}`,
              value: `${Math.round(score * 100)}%`,
              color: score >= 0.75 ? "green" : score >= 0.5 ? "blue" : "amber",
            }))
          : []),
        quality.interaction_rate != null && {
          label: "Interaction Rate",
          value: fmtPct(quality.interaction_rate),
          color: quality.interaction_rate >= 30 ? "green" : quality.interaction_rate >= 15 ? "blue" : "amber",
        },
        quality.bookmark_rate != null && {
          label: "Bookmark Rate",
          value: fmtPct(quality.bookmark_rate),
          color: quality.bookmark_rate >= 20 ? "green" : quality.bookmark_rate >= 10 ? "blue" : "amber",
        },
      ].filter(Boolean)
    : [];

  // ── Total pages for interactions ──────────────────────────────────────────────

  const totalPages = Math.max(1, Math.ceil(intTotal / PAGE_SIZE));

  // ─────────────────────────────────────────────────────────────────────────────

  return (
    <AdministrationLayout
      title="Recommendation Center"
      subtitle="Read-only analytics dashboard for the academic recommendation engine."
    >
      {/* ── Top metric cards ──────────────────────────────────── */}
      <section>
        <div className="overline mb-3">Platform Overview</div>
        {statsError ? (
          <ErrorCard message={statsError} onRetry={fetchStats} />
        ) : (
          <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <MetricCard
              icon={Activity}
              label="Total Interactions"
              value={totalInteractions != null ? totalInteractions.toLocaleString() : "—"}
              loading={statsLoading}
              color="blue"
            />
            <MetricCard
              icon={ThumbsUp}
              label="Acceptance Rate"
              value={acceptanceRate != null ? `${acceptanceRate}%` : "—"}
              sub={totalAccepted != null ? `${totalAccepted.toLocaleString()} accepted` : undefined}
              loading={statsLoading}
              color="green"
            />
            <MetricCard
              icon={Users}
              label="Profile Coverage"
              value={coveragePct != null ? `${Math.round(coveragePct)}%` : "—"}
              sub={coverage?.total_users != null ? `${coverage.total_users.toLocaleString()} users` : undefined}
              loading={coverageLoading}
              color="amber"
            />
            <MetricCard
              icon={XCircle}
              label="Dismissal Rate"
              value={dismissalRate != null ? `${dismissalRate}%` : "—"}
              sub={totalDismissals != null ? `${totalDismissals.toLocaleString()} dismissed` : undefined}
              loading={statsLoading}
              color="red"
            />
          </div>
        )}
      </section>

      {/* ── Charts section ────────────────────────────────────── */}
      <section>
        <div className="overline mb-3">Interaction Analytics</div>
        <div className="grid lg:grid-cols-2 gap-6">

          {/* Chart 1: Interactions by Type */}
          <div className="border border-slate-200 bg-white p-5">
            <h3 className="font-medium text-slate-900 mb-4 text-sm">Interactions by Type</h3>
            {byTypeError ? (
              <ErrorCard message={byTypeError} onRetry={fetchByType} />
            ) : (
              <InteractionsByTypeChart data={byType} loading={byTypeLoading} />
            )}
          </div>

          {/* Chart 2: Acceptance Rate by Type */}
          <div className="border border-slate-200 bg-white p-5">
            <h3 className="font-medium text-slate-900 mb-4 text-sm">Acceptance Rate by Type</h3>
            {byTypeError ? (
              <ErrorCard message={byTypeError} onRetry={fetchByType} />
            ) : (
              <AcceptanceByTypeChart data={byType} loading={byTypeLoading} />
            )}
          </div>
        </div>

        {/* Chart 3: Top Research Areas */}
        <div className="border border-slate-200 bg-white p-5 mt-6">
          <h3 className="font-medium text-slate-900 mb-4 text-sm">Top Research Areas in Profiles</h3>
          {topAreasError ? (
            <ErrorCard message={topAreasError} onRetry={fetchTopAreas} />
          ) : (
            <TopAreasChart data={topAreas} loading={topAreasLoading} />
          )}
        </div>
      </section>

      {/* ── Quality Metrics ───────────────────────────────────── */}
      <section>
        <div className="overline mb-3">Quality Metrics</div>
        {qualityError ? (
          <ErrorCard message={qualityError} onRetry={fetchQuality} />
        ) : qualityLoading ? (
          <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-3">
            {Array.from({ length: 8 }).map((_, i) => (
              <div key={i} className="border border-slate-200 bg-white p-3">
                <SkeletonBlock className="h-3 w-24 mb-2" />
                <SkeletonBlock className="h-6 w-16" />
              </div>
            ))}
          </div>
        ) : qualityItems.length === 0 ? (
          <p className="text-slate-400 text-sm">No quality metrics available yet.</p>
        ) : (
          <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-3">
            {qualityItems.map((q) => (
              <QualityBadge key={q.label} label={q.label} value={q.value} color={q.color} />
            ))}
          </div>
        )}
      </section>

      {/* ── Tables section ────────────────────────────────────── */}
      <section>
        <div className="overline mb-3">Recent Interactions</div>
        <div className="border border-slate-200 bg-white overflow-hidden">
          {intError ? (
            <div className="p-6">
              <ErrorCard message={intError} onRetry={() => fetchInteractions(intPage)} />
            </div>
          ) : (
            <>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-slate-200 bg-slate-50">
                      <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wide">Type</th>
                      <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wide">Target</th>
                      <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wide">Action</th>
                      <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wide">User</th>
                      <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wide">Timestamp</th>
                    </tr>
                  </thead>
                  <tbody>
                    {intLoading
                      ? Array.from({ length: 10 }).map((_, i) => (
                          <tr key={i} className="border-b border-slate-100">
                            {[1, 2, 3, 4, 5].map((j) => (
                              <td key={j} className="px-4 py-3">
                                <SkeletonBlock className="h-4 w-full" />
                              </td>
                            ))}
                          </tr>
                        ))
                      : interactions.length === 0
                      ? (
                        <tr>
                          <td colSpan={5} className="px-4 py-10 text-center text-slate-400 text-sm">
                            No interactions recorded yet.
                          </td>
                        </tr>
                      )
                      : interactions.map((row, i) => {
                          const actionColor = {
                            accepted:   "text-emerald-700 bg-emerald-50",
                            bookmarked: "text-blue-700 bg-blue-50",
                            dismissed:  "text-red-700 bg-red-50",
                            clicked:    "text-slate-700 bg-slate-100",
                          }[row.action] || "text-slate-700 bg-slate-100";

                          return (
                            <tr key={row.id || i} className="border-b border-slate-100 hover:bg-slate-50 transition-colors">
                              <td className="px-4 py-3">
                                <span className="text-xs font-medium capitalize text-slate-700">
                                  {fmt(row.rec_type || row.type)}
                                </span>
                              </td>
                              <td className="px-4 py-3 max-w-[200px]">
                                <span className="text-xs text-slate-600 truncate block">
                                  {fmt(row.target_name || row.rec_id || row.target)}
                                </span>
                              </td>
                              <td className="px-4 py-3">
                                <span className={`inline-flex items-center px-2 py-0.5 text-xs rounded-full font-medium ${actionColor}`}>
                                  {fmt(row.action)}
                                </span>
                              </td>
                              <td className="px-4 py-3">
                                <span className="text-xs text-slate-600 truncate block max-w-[160px]">
                                  {fmt(row.user_email || row.user_name || row.user_id)}
                                </span>
                              </td>
                              <td className="px-4 py-3">
                                <span className="text-xs font-mono text-slate-500">
                                  {formatDate(row.created_at || row.timestamp)}
                                </span>
                              </td>
                            </tr>
                          );
                        })}
                  </tbody>
                </table>
              </div>

              {/* Pagination */}
              {totalPages > 1 && (
                <div className="flex items-center justify-between px-4 py-3 border-t border-slate-200 bg-slate-50">
                  <div className="text-xs text-slate-500">
                    Page {intPage} of {totalPages} ({intTotal.toLocaleString()} total)
                  </div>
                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => setIntPage((p) => Math.max(1, p - 1))}
                      disabled={intPage <= 1 || intLoading}
                      className="inline-flex items-center gap-1 px-3 py-1.5 text-xs border border-slate-300 text-slate-700 hover:border-[#0F2847] hover:text-[#0F2847] disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
                    >
                      <ChevronLeft size={12} /> Previous
                    </button>
                    <button
                      onClick={() => setIntPage((p) => Math.min(totalPages, p + 1))}
                      disabled={intPage >= totalPages || intLoading}
                      className="inline-flex items-center gap-1 px-3 py-1.5 text-xs border border-slate-300 text-slate-700 hover:border-[#0F2847] hover:text-[#0F2847] disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
                    >
                      Next <ChevronRight size={12} />
                    </button>
                  </div>
                </div>
              )}
            </>
          )}
        </div>
      </section>

      {/* ── Profile Coverage Details ──────────────────────────── */}
      <section>
        <div className="overline mb-3">Profile Coverage Details</div>
        <div className="border border-slate-200 bg-white p-5">
          {coverageError ? (
            <ErrorCard message={coverageError} onRetry={fetchCoverage} />
          ) : coverageLoading ? (
            <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-5">
              {Array.from({ length: 4 }).map((_, i) => (
                <div key={i}>
                  <SkeletonBlock className="h-3 w-24 mb-2" />
                  <SkeletonBlock className="h-7 w-16" />
                </div>
              ))}
            </div>
          ) : (
            <>
              <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-5">
                <div>
                  <div className="text-xs text-slate-500 mb-1">Total Users</div>
                  <div className="text-2xl font-bold font-mono text-slate-900">
                    {coverage?.total_users != null ? coverage.total_users.toLocaleString() : "—"}
                  </div>
                </div>
                <div>
                  <div className="text-xs text-slate-500 mb-1">Profiles Built</div>
                  <div className="text-2xl font-bold font-mono text-emerald-700">
                    {coverage?.profiles_built != null ? coverage.profiles_built.toLocaleString() : "—"}
                  </div>
                </div>
                <div>
                  <div className="text-xs text-slate-500 mb-1">Stale Profiles</div>
                  <div className="text-2xl font-bold font-mono text-amber-700">
                    {coverage?.stale_profiles != null ? coverage.stale_profiles.toLocaleString() : "—"}
                  </div>
                </div>
                <div>
                  <div className="text-xs text-slate-500 mb-1">Fresh Profiles</div>
                  <div className="text-2xl font-bold font-mono text-blue-700">
                    {coverage?.fresh_profiles != null ? coverage.fresh_profiles.toLocaleString() : "—"}
                  </div>
                </div>
              </div>

              {/* Coverage bar */}
              {coveragePct != null && (
                <div className="mb-5">
                  <div className="flex items-center justify-between text-xs text-slate-500 mb-1">
                    <span>Coverage</span>
                    <span className="font-mono">{Math.round(coveragePct)}%</span>
                  </div>
                  <div className="h-3 bg-slate-100 w-full overflow-hidden">
                    <div
                      className="h-full bg-[#0F2847] transition-all duration-700"
                      style={{ width: `${Math.min(coveragePct, 100)}%` }}
                    />
                  </div>
                </div>
              )}

              <button
                onClick={handleRefreshAll}
                disabled={refreshingAll}
                className="inline-flex items-center gap-2 border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-700 hover:border-[#0F2847] hover:text-[#0F2847] disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                <RefreshCw size={14} strokeWidth={1.5} className={refreshingAll ? "animate-spin" : ""} />
                {refreshingAll ? "Refreshing profiles…" : "Refresh All Profiles"}
              </button>
            </>
          )}
        </div>
      </section>
    </AdministrationLayout>
  );
}
