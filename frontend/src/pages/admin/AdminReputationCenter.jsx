/* eslint-disable */
import { useState, useEffect, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import api from "@/lib/api";
import { toast } from "sonner";
import { getResearchLevel } from "@/hooks/useReputation";
import { NAVY } from "@/lib/tokens";
import { AdministrationLayout } from "@/layouts";
import {
  Card, Button, Alert, NavTabs, StatCard, StatGrid,
  DataTable, ProgressBar, SkeletonLine,
} from "@/components/ds";

// ── Helpers ───────────────────────────────────────────────────────────────────

function formatDate(iso) {
  if (!iso) return "—";
  return new Date(iso).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
}

// NOTE: LevelPill keeps its own hand-rolled span rather than wrapping in
// ds/Badge — getResearchLevel()'s `tone` return value is itself a full
// background/border/text utility bundle, and layering it on top of Badge's
// own variant classes (same utility slots, equal Tailwind specificity) would
// make the resulting color non-deterministic. Same exception applied in
// AdminReputation.jsx.
function LevelPill({ score }) {
  const lvl = getResearchLevel(score || 0);
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded-full border text-xs font-medium ${lvl.tone}`}>
      Lv {lvl.level} · {lvl.short}
    </span>
  );
}

// ── Bar for level distribution ────────────────────────────────────────────────
// NOTE: kept as a hand-rolled bar list (not ds/Chart's recharts-based
// BarChart) — each row needs a custom per-level color keyed off level number,
// which ds/BarChart's single-series data shape doesn't express.

const LEVEL_COLORS = [
  "bg-slate-400",
  "bg-emerald-500",
  "bg-blue-500",
  "bg-indigo-500",
  "bg-violet-500",
  "bg-amber-500",
  "bg-yellow-500",
];

function LevelDistributionChart({ distribution }) {
  if (!distribution || distribution.length === 0) {
    return <p className="text-slate-400 text-sm text-center py-6">No data.</p>;
  }
  const max = Math.max(...distribution.map((d) => d.count || 0), 1);
  return (
    <div className="space-y-3">
      {distribution.map((d) => {
        const pct = Math.round(((d.count || 0) / max) * 100);
        const color = LEVEL_COLORS[(d.level - 1) % LEVEL_COLORS.length] || "bg-slate-400";
        return (
          <div key={d.level} className="flex items-center gap-3">
            <div className="w-32 text-sm text-slate-700 flex-shrink-0">
              Lv {d.level} · {d.label}
            </div>
            <div className="flex-1 h-5 bg-slate-100 rounded-full overflow-hidden">
              <div
                className={`h-full ${color} rounded-full transition-all duration-700`}
                style={{ width: `${pct}%` }}
              />
            </div>
            <div className="w-16 text-right text-sm font-medium text-slate-700">
              {(d.count || 0).toLocaleString()}
            </div>
          </div>
        );
      })}
    </div>
  );
}

// ── TABS ──────────────────────────────────────────────────────────────────────

const TABS = [
  { id: "stats",     label: "Platform Stats" },
  { id: "top",       label: "Top Researchers" },
  { id: "fraud",     label: "Fraud Alerts" },
  { id: "fastest",   label: "Fastest Growing" },
];

// ── Main component ────────────────────────────────────────────────────────────

export default function AdminReputationCenter() {
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState("stats");

  // data state
  const [stats,      setStats]      = useState(null);
  const [topUsers,   setTopUsers]   = useState([]);
  const [badgeDist,  setBadgeDist]  = useState([]);
  const [fraudAlerts,setFraudAlerts]= useState([]);
  const [fastest,    setFastest]    = useState([]);
  const [loading,    setLoading]    = useState({});
  const [computing,  setComputing]  = useState(false);

  const setTabLoading = (tab, val) =>
    setLoading((prev) => ({ ...prev, [tab]: val }));

  // ── Fetch helpers ─────────────────────────────────────────────────────────

  const fetchStats = useCallback(async () => {
    setTabLoading("stats", true);
    try {
      const [statsRes, badgeRes] = await Promise.all([
        api.get("/admin/reputation/stats"),
        api.get("/admin/reputation/badge-distribution"),
      ]);
      setStats(statsRes.data);
      setBadgeDist(Array.isArray(badgeRes.data) ? badgeRes.data : []);
    } catch {
      toast.error("Failed to load platform stats");
    } finally {
      setTabLoading("stats", false);
    }
  }, []);

  const fetchTop = useCallback(async () => {
    setTabLoading("top", true);
    try {
      const { data } = await api.get("/admin/reputation/top-researchers");
      setTopUsers(Array.isArray(data) ? data : []);
    } catch {
      toast.error("Failed to load top researchers");
    } finally {
      setTabLoading("top", false);
    }
  }, []);

  const fetchFraud = useCallback(async () => {
    setTabLoading("fraud", true);
    try {
      const { data } = await api.get("/admin/reputation/fraud-alerts");
      setFraudAlerts(Array.isArray(data) ? data : []);
    } catch {
      toast.error("Failed to load fraud alerts");
    } finally {
      setTabLoading("fraud", false);
    }
  }, []);

  const fetchFastest = useCallback(async () => {
    setTabLoading("fastest", true);
    try {
      const { data } = await api.get("/admin/reputation/fastest-growing");
      setFastest(Array.isArray(data) ? data : []);
    } catch {
      toast.error("Failed to load fastest growing data");
    } finally {
      setTabLoading("fastest", false);
    }
  }, []);

  // Initial load per tab
  useEffect(() => {
    if (activeTab === "stats")   fetchStats();
    if (activeTab === "top")     fetchTop();
    if (activeTab === "fraud")   fetchFraud();
    if (activeTab === "fastest") fetchFastest();
  }, [activeTab, fetchStats, fetchTop, fetchFraud, fetchFastest]);

  // ── Actions ───────────────────────────────────────────────────────────────

  const handleComputeRankings = async () => {
    setComputing(true);
    try {
      await api.post("/admin/reputation/rankings/compute");
      toast.success("Ranking recomputation triggered successfully");
      // Refresh stats after recompute
      await fetchStats();
    } catch {
      toast.error("Failed to trigger ranking recomputation");
    } finally {
      setComputing(false);
    }
  };

  // ── Tab: Platform Stats ───────────────────────────────────────────────────

  const badgeColumns = [
    { key: "badge_label", label: "Badge", render: (_, b) => <span className="font-medium text-slate-800">{b.badge_label || b.badge_code}</span> },
    { key: "badge_code", label: "Code", render: (v) => <span className="text-xs font-mono text-slate-500">{v}</span> },
    { key: "count", label: "Count Awarded", align: "right", render: (v) => <span className="font-bold text-[#0F2847]">{(v || 0).toLocaleString()}</span> },
  ];

  const renderStats = () => {
    const isLoading = loading.stats;
    return (
      <div className="space-y-6">
        {/* Integrity notice */}
        <Alert variant="warning" title="Integrity notice">
          Reputation scores cannot be manually modified. All values derive from verified platform
          activity. Score manipulation is not supported.
        </Alert>

        {/* KPI cards */}
        <StatGrid cols={4}>
          <StatCard label="Users with Scores" value={isLoading ? "…" : (stats?.total_users_with_scores?.toLocaleString() ?? "—")} />
          <StatCard label="Total Events" value={isLoading ? "…" : (stats?.total_events?.toLocaleString() ?? "—")} />
          <StatCard label="Average Score" value={isLoading ? "…" : (stats?.avg_score != null ? stats.avg_score.toFixed(1) : "—")} />
          <StatCard label="Level Distribution" value={isLoading ? "…" : (stats?.level_distribution?.length ?? "—")} sub="levels tracked" />
        </StatGrid>

        {/* Level distribution chart */}
        <Card padding="lg">
          <h3 className="font-semibold text-slate-900 mb-4">Level Distribution</h3>
          {isLoading
            ? <SkeletonLine height={192} />
            : <LevelDistributionChart distribution={stats?.level_distribution} />
          }
        </Card>

        {/* Badge distribution table */}
        <Card padding="lg">
          <h3 className="font-semibold text-slate-900 mb-4">Badge Distribution</h3>
          <DataTable
            columns={badgeColumns}
            rows={badgeDist}
            loading={isLoading}
            emptyNode={<p className="text-slate-400 text-sm text-center py-6">No badge data available.</p>}
          />
        </Card>

        {/* Recompute action */}
        <Card padding="lg" className="flex items-center justify-between gap-4 flex-wrap">
          <div>
            <h3 className="font-semibold text-slate-900">Recompute Global Rankings</h3>
            <p className="text-sm text-slate-500 mt-1">
              Trigger a fresh ranking computation across all users. This may take a few minutes.
            </p>
          </div>
          <Button variant="primary" onClick={handleComputeRankings} disabled={computing} loading={computing}>
            {computing ? "Computing…" : "Recompute Rankings"}
          </Button>
        </Card>
      </div>
    );
  };

  // ── Tab: Top Researchers ──────────────────────────────────────────────────

  const topColumns = [
    { key: "_rank", label: "Rank", render: (_, u) => <span className="font-bold text-slate-500">#{topUsers.indexOf(u) + 1}</span> },
    { key: "full_name", label: "Name", render: (v) => <span className="font-medium text-slate-900">{v || "—"}</span> },
    { key: "email", label: "Email", render: (v) => <span className="text-xs text-slate-500">{v || "—"}</span> },
    { key: "overall_score", label: "Score", align: "right", render: (v) => <span className="font-bold text-[#0F2847]">{(v || 0).toLocaleString()}</span> },
    { key: "_level", label: "Level", align: "center", render: (_, u) => <LevelPill score={u.overall_score} /> },
    { key: "institution", label: "Institution", render: (v) => <span className="text-xs text-slate-600">{v || "—"}</span> },
    { key: "country", label: "Country", render: (v) => <span className="text-xs text-slate-600">{v || "—"}</span> },
    {
      key: "_actions", label: "Actions", align: "center",
      render: (_, u) => (
        <Button variant="link" size="sm" onClick={() => navigate(`/admin/users/${u.user_id}`)}>
          View Profile
        </Button>
      ),
    },
  ];

  const renderTop = () => {
    const isLoading = loading.top;
    return (
      <Card padding="none">
        <div className="p-4 border-b border-slate-200 flex items-center justify-between">
          <h3 className="font-semibold text-slate-900">Top 50 Researchers</h3>
          <Button variant="link" size="sm" onClick={fetchTop}>↻ Refresh</Button>
        </div>
        <DataTable
          columns={topColumns}
          rows={topUsers}
          loading={isLoading}
          emptyNode={<div className="text-center text-slate-400 py-12">No data available.</div>}
        />
      </Card>
    );
  };

  // ── Tab: Fraud Alerts ─────────────────────────────────────────────────────

  const fraudColumns = [
    { key: "full_name", label: "User", render: (_, a) => <span className="font-medium text-slate-900">{a.full_name || a.user_id || "—"}</span> },
    { key: "email", label: "Email", render: (v) => <span className="text-xs text-slate-500">{v || "—"}</span> },
    { key: "total_events_7d", label: "Events (7d)", align: "right", render: (v) => <span className="font-bold text-red-600">{v ?? "—"}</span> },
    {
      key: "flag_reason", label: "Flag Reason",
      render: (v) => <span className="text-xs text-red-700 bg-red-50 border border-red-100 px-2 py-1 rounded-lg">{v || "Unusual activity"}</span>,
    },
    {
      key: "_actions", label: "Actions", align: "center",
      render: (_, a) => (
        <Button variant="link" size="sm" onClick={() => navigate(`/admin/users/${a.user_id}`)}>
          View Profile
        </Button>
      ),
    },
  ];

  const renderFraud = () => {
    const isLoading = loading.fraud;
    return (
      <div className="space-y-4">
        {/* Note */}
        <Alert variant="error" title="Fraud Detection Alerts">
          Users flagged for unusual activity patterns. Review their profiles for further investigation.
          Reputation scores cannot be manually adjusted — all values reflect verified activity.
        </Alert>

        <Card padding="none">
          <div className="p-4 border-b border-slate-200 flex items-center justify-between">
            <h3 className="font-semibold text-slate-900">
              Flagged Users
              {fraudAlerts.length > 0 && (
                <span className="ml-2 text-xs font-normal text-red-600 bg-red-50 border border-red-200 px-2 py-0.5 rounded-full">
                  {fraudAlerts.length} alerts
                </span>
              )}
            </h3>
            <Button variant="link" size="sm" onClick={fetchFraud}>↻ Refresh</Button>
          </div>
          <DataTable
            columns={fraudColumns}
            rows={fraudAlerts}
            loading={isLoading}
            emptyNode={<div className="text-center text-slate-400 py-12">No fraud alerts at this time.</div>}
          />
        </Card>
      </div>
    );
  };

  // ── Tab: Fastest Growing ──────────────────────────────────────────────────

  const fastestColumns = [
    { key: "_rank", label: "#", render: (_, u) => <span className="font-bold text-slate-500">#{fastest.indexOf(u) + 1}</span> },
    { key: "full_name", label: "Name", render: (v) => <span className="font-medium text-slate-900">{v || "—"}</span> },
    { key: "email", label: "Email", render: (v) => <span className="text-xs text-slate-500">{v || "—"}</span> },
    { key: "overall_score", label: "Current Score", align: "right", render: (v) => <span className="font-bold text-[#0F2847]">{(v || 0).toLocaleString()}</span> },
    {
      key: "points_gained_30d", label: "+Points (30d)", align: "right",
      render: (_, u) => <span className="font-bold text-emerald-600">+{(u.points_gained_30d || u.points_30d || 0).toLocaleString()}</span>,
    },
    { key: "_level", label: "Level", align: "center", render: (_, u) => <LevelPill score={u.overall_score} /> },
    { key: "institution", label: "Institution", render: (v) => <span className="text-xs text-slate-600">{v || "—"}</span> },
    {
      key: "_actions", label: "Actions", align: "center",
      render: (_, u) => (
        <Button variant="link" size="sm" onClick={() => navigate(`/admin/users/${u.user_id}`)}>
          View Profile
        </Button>
      ),
    },
  ];

  const renderFastest = () => {
    const isLoading = loading.fastest;
    return (
      <Card padding="none">
        <div className="p-4 border-b border-slate-200 flex items-center justify-between">
          <div>
            <h3 className="font-semibold text-slate-900">Fastest Growing Researchers</h3>
            <p className="text-xs text-slate-500 mt-0.5">Top 20 by points gained in the last 30 days</p>
          </div>
          <Button variant="link" size="sm" onClick={fetchFastest}>↻ Refresh</Button>
        </div>
        <DataTable
          columns={fastestColumns}
          rows={fastest}
          loading={isLoading}
          emptyNode={<div className="text-center text-slate-400 py-12">No data available.</div>}
        />
      </Card>
    );
  };

  // ── Render ────────────────────────────────────────────────────────────────

  const navTabs = TABS.map((t) => ({
    ...t,
    count: t.id === "fraud" && fraudAlerts.length > 0 ? fraudAlerts.length : undefined,
  }));

  return (
    <AdministrationLayout
      title="Reputation Center"
      subtitle="Platform-wide reputation analytics and monitoring"
      actions={
        <span className="text-xs text-slate-400 bg-white border border-slate-200 px-3 py-1.5 rounded-lg">
          Admin view — read-only scores
        </span>
      }
    >
        {/* Tabs */}
        <NavTabs
          tabs={navTabs}
          active={activeTab}
          onChange={setActiveTab}
          variant="segment"
          className="mb-6"
        />

        {/* Tab content */}
        <div>
          {activeTab === "stats"   && renderStats()}
          {activeTab === "top"     && renderTop()}
          {activeTab === "fraud"   && renderFraud()}
          {activeTab === "fastest" && renderFastest()}
        </div>
    </AdministrationLayout>
  );
}
