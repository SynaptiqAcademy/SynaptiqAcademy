import { useState, useEffect, useCallback } from "react";
import api from "@/lib/api";
import { toast } from "sonner";
import { NAVY } from "@/lib/tokens";
import {
  Percent, TrendingUp,
  RefreshCw, AlertCircle, ChevronLeft, ChevronRight,
} from "lucide-react";
import { AdministrationLayout } from "@/layouts";
import {
  Card, Button, Badge, ErrorState, Skeleton,
  DataTable, Pagination, ProgressBar,
} from "@/components/ds";

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

// Thin adapter over ds/Skeleton preserving the original `className="h-# w-#"`
// call sites used throughout this file's custom charts.
function SkeletonBlock({ className = "" }) {
  return <Skeleton height="" width="" className={className} />;
}

function ErrorCard({ message, onRetry }) {
  return <ErrorState message={message || "Failed to load data."} onRetry={onRetry} />;
}

// ── Horizontal bar chart (div-based) ─────────────────────────────────────────
// NOTE: these three charts render custom segmented/stacked percentage bars
// driven by arbitrary per-row breakdowns (accepted/bookmarked/dismissed/clicked
// sub-widths, ranked area lists). The ds/ Chart.jsx components (BarChart,
// DonutChart, etc.) are recharts-based single-series charts and don't expose
// a stacked-segment-per-row API, so the bar rendering here is left hand-rolled;
// only their containers are migrated to Card.

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

const QUALITY_BADGE_VARIANT = { green: "success", blue: "info", amber: "warning", slate: "neutral" };

function QualityBadge({ label, value, color }) {
  return (
    <Card padding="sm">
      <div className="text-xs text-slate-500 mb-1">{label}</div>
      <Badge variant={QUALITY_BADGE_VARIANT[color] || "neutral"} size="md" className="text-sm font-bold">
        {value}
      </Badge>
    </Card>
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

  // ── Interactions table columns ─────────────────────────────────────────────

  const ACTION_BADGE_VARIANT = { accepted: "success", bookmarked: "info", dismissed: "danger", clicked: "neutral" };

  const interactionColumns = [
    {
      key: "rec_type",
      label: "Type",
      render: (_, row) => <span className="font-medium capitalize">{fmt(row.rec_type || row.type)}</span>,
    },
    {
      key: "target_name",
      label: "Target",
      maxWidth: 200,
      render: (_, row) => fmt(row.target_name || row.rec_id || row.target),
    },
    {
      key: "action",
      label: "Action",
      render: (_, row) => <Badge variant={ACTION_BADGE_VARIANT[row.action] || "neutral"} size="sm">{fmt(row.action)}</Badge>,
    },
    {
      key: "user_email",
      label: "User",
      maxWidth: 160,
      render: (_, row) => fmt(row.user_email || row.user_name || row.user_id),
    },
    {
      key: "created_at",
      label: "Timestamp",
      render: (_, row) => <span className="font-mono text-xs">{formatDate(row.created_at || row.timestamp)}</span>,
    },
  ];

  // ─────────────────────────────────────────────────────────────────────────────

  return (
    <AdministrationLayout
      title="Recommendation Center"
      subtitle="Read-only analytics dashboard for the academic recommendation engine."
      stats={[
        { label: "Total Interactions", value: statsLoading ? "…" : (totalInteractions != null ? totalInteractions.toLocaleString() : "—") },
        { label: "Acceptance Rate",    value: statsLoading ? "…" : (acceptanceRate != null ? `${acceptanceRate}%` : "—") },
        { label: "Profile Coverage",   value: coverageLoading ? "…" : (coveragePct != null ? `${Math.round(coveragePct)}%` : "—") },
        { label: "Dismissal Rate",     value: statsLoading ? "…" : (dismissalRate != null ? `${dismissalRate}%` : "—") },
      ]}
      sidebar={<RecommendationCenterSidebar qualityItems={qualityItems} qualityLoading={qualityLoading} topAreas={topAreas} topAreasLoading={topAreasLoading} />}
    >
      {/* ── Platform Overview errors ──────────────────────────── */}
      {statsError && (
        <section>
          <div className="overline mb-3">Platform Overview</div>
          <ErrorCard message={statsError} onRetry={fetchStats} />
        </section>
      )}

      {/* ── Charts section ────────────────────────────────────── */}
      <section>
        <div className="overline mb-3">Interaction Analytics</div>
        <div className="grid lg:grid-cols-2 gap-6">

          {/* Chart 1: Interactions by Type */}
          <Card padding="lg">
            <h3 className="font-medium text-slate-900 mb-4 text-sm">Interactions by Type</h3>
            {byTypeError ? (
              <ErrorCard message={byTypeError} onRetry={fetchByType} />
            ) : (
              <InteractionsByTypeChart data={byType} loading={byTypeLoading} />
            )}
          </Card>

          {/* Chart 2: Acceptance Rate by Type */}
          <Card padding="lg">
            <h3 className="font-medium text-slate-900 mb-4 text-sm">Acceptance Rate by Type</h3>
            {byTypeError ? (
              <ErrorCard message={byTypeError} onRetry={fetchByType} />
            ) : (
              <AcceptanceByTypeChart data={byType} loading={byTypeLoading} />
            )}
          </Card>
        </div>

        {/* Chart 3: Top Research Areas */}
        <Card padding="lg" className="mt-6">
          <h3 className="font-medium text-slate-900 mb-4 text-sm">Top Research Areas in Profiles</h3>
          {topAreasError ? (
            <ErrorCard message={topAreasError} onRetry={fetchTopAreas} />
          ) : (
            <TopAreasChart data={topAreas} loading={topAreasLoading} />
          )}
        </Card>
      </section>

      {/* ── Quality Metrics ───────────────────────────────────── */}
      <section>
        <div className="overline mb-3">Quality Metrics</div>
        {qualityError ? (
          <ErrorCard message={qualityError} onRetry={fetchQuality} />
        ) : qualityLoading ? (
          <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-3">
            {Array.from({ length: 8 }).map((_, i) => (
              <Card key={i} padding="sm">
                <SkeletonBlock className="h-3 w-24 mb-2" />
                <SkeletonBlock className="h-6 w-16" />
              </Card>
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
        {intError ? (
          <Card padding="lg">
            <ErrorCard message={intError} onRetry={() => fetchInteractions(intPage)} />
          </Card>
        ) : (
          <div className="flex flex-col gap-3">
            <DataTable
              columns={interactionColumns}
              rows={interactions}
              loading={intLoading}
              emptyNode={
                <div className="px-4 py-10 text-center text-slate-400 text-sm">
                  No interactions recorded yet.
                </div>
              }
            />
            {totalPages > 1 && (
              <div className="flex items-center justify-between px-1 py-1">
                <div className="text-xs text-slate-500">
                  Page {intPage} of {totalPages} ({intTotal.toLocaleString()} total)
                </div>
                <Pagination page={intPage} totalPages={totalPages} onPage={(p) => setIntPage(p)} />
              </div>
            )}
          </div>
        )}
      </section>

      {/* ── Profile Coverage Details ──────────────────────────── */}
      <section>
        <div className="overline mb-3">Profile Coverage Details</div>
        <Card padding="lg">
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
                  <ProgressBar value={Math.min(coveragePct, 100)} max={100} label="Coverage" />
                </div>
              )}

              <Button variant="ghost" onClick={handleRefreshAll} disabled={refreshingAll}>
                <RefreshCw size={14} strokeWidth={1.5} className={refreshingAll ? "animate-spin" : ""} />
                {refreshingAll ? "Refreshing profiles…" : "Refresh All Profiles"}
              </Button>
            </>
          )}
        </Card>
      </section>
    </AdministrationLayout>
  );
}

// ── Right rail — quality signals & top areas, real data already fetched above ──
function RecommendationCenterSidebar({ qualityItems, qualityLoading, topAreas, topAreasLoading }) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      <Card padding="lg">
        <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 8 }}>
          <Percent size={13} style={{ color: NAVY }} />
          <div style={{ fontSize: 13, fontWeight: 700, color: "#0f172a" }}>Quality Signals</div>
        </div>
        {qualityLoading ? (
          <p style={{ fontSize: 12, color: "#94A3B8", margin: 0 }}>Loading…</p>
        ) : qualityItems.length === 0 ? (
          <p style={{ fontSize: 12, color: "#94A3B8", margin: 0, lineHeight: 1.5 }}>
            No quality metrics available yet.
          </p>
        ) : (
          <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
            {qualityItems.slice(0, 5).map((q) => (
              <div key={q.label} style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 8 }}>
                <span style={{ fontSize: 11.5, color: "#64748B" }}>{q.label}</span>
                <span style={{ fontSize: 12, fontWeight: 700, color: "#0f172a" }}>{q.value}</span>
              </div>
            ))}
          </div>
        )}
      </Card>

      <Card padding="lg">
        <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 8 }}>
          <TrendingUp size={13} style={{ color: NAVY }} />
          <div style={{ fontSize: 13, fontWeight: 700, color: "#0f172a" }}>Top Research Areas</div>
        </div>
        {topAreasLoading ? (
          <p style={{ fontSize: 12, color: "#94A3B8", margin: 0 }}>Loading…</p>
        ) : topAreas.length === 0 ? (
          <p style={{ fontSize: 12, color: "#94A3B8", margin: 0, lineHeight: 1.5 }}>
            No area data yet.
          </p>
        ) : (
          <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
            {topAreas.slice(0, 5).map((d, i) => (
              <div key={d.area || d.name || i} style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 8 }}>
                <span style={{ fontSize: 11.5, color: "#374151", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{d.area || d.name || "Unknown"}</span>
                <span style={{ fontSize: 11, color: "#94A3B8", fontFamily: "monospace" }}>{(d.count || 0).toLocaleString()}</span>
              </div>
            ))}
          </div>
        )}
      </Card>
    </div>
  );
}
