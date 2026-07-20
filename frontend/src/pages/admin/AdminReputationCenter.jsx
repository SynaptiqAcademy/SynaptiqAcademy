/* eslint-disable */
import { useState, useEffect, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import api from "@/lib/api";
import { toast } from "sonner";
import { getResearchLevel } from "@/hooks/useReputation";
import { NAVY } from "@/lib/tokens";
import { AdministrationLayout } from "@/layouts";

// ── Helpers ───────────────────────────────────────────────────────────────────

function formatDate(iso) {
  if (!iso) return "—";
  return new Date(iso).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
}

function LevelPill({ score }) {
  const lvl = getResearchLevel(score || 0);
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded-full border text-xs font-medium ${lvl.tone}`}>
      Lv {lvl.level} · {lvl.short}
    </span>
  );
}

function SkeletonBlock({ className = "" }) {
  return <div className={`animate-pulse bg-slate-200 rounded ${className}`} />;
}

// ── Bar for level distribution ────────────────────────────────────────────────

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

  const renderStats = () => {
    const isLoading = loading.stats;
    return (
      <div className="space-y-6">
        {/* Integrity notice */}
        <div className="bg-amber-50 border border-amber-200 rounded-md p-4 flex gap-3 items-start">
          <span className="text-amber-600 text-lg flex-shrink-0 mt-0.5">⚠</span>
          <p className="text-sm text-amber-800">
            <strong>Integrity notice:</strong> Reputation scores cannot be manually modified.
            All values derive from verified platform activity. Score manipulation is not supported.
          </p>
        </div>

        {/* KPI cards */}
        {isLoading ? (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {[1,2,3,4].map(i => <SkeletonBlock key={i} className="h-24 rounded-md" />)}
          </div>
        ) : (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {[
              { label: "Users with Scores", value: stats?.total_users_with_scores?.toLocaleString() ?? "—" },
              { label: "Total Events",       value: stats?.total_events?.toLocaleString() ?? "—" },
              { label: "Average Score",      value: stats?.avg_score != null ? stats.avg_score.toFixed(1) : "—" },
              { label: "Level Distribution", value: stats?.level_distribution?.length ?? "—", sub: "levels tracked" },
            ].map(({ label, value, sub }) => (
              <div key={label} className="bg-white border border-slate-200 rounded-md p-4 text-center">
                <div className="text-2xl font-bold text-slate-900">{value}</div>
                <div className="text-xs font-medium text-slate-500 mt-1">{label}</div>
                {sub && <div className="text-xs text-slate-400 mt-0.5">{sub}</div>}
              </div>
            ))}
          </div>
        )}

        {/* Level distribution chart */}
        <div className="bg-white border border-slate-200 rounded-md p-6">
          <h3 className="font-semibold text-slate-900 mb-4">Level Distribution</h3>
          {isLoading
            ? <SkeletonBlock className="h-48 rounded-md" />
            : <LevelDistributionChart distribution={stats?.level_distribution} />
          }
        </div>

        {/* Badge distribution table */}
        <div className="bg-white border border-slate-200 rounded-md p-6">
          <h3 className="font-semibold text-slate-900 mb-4">Badge Distribution</h3>
          {isLoading ? (
            <SkeletonBlock className="h-40 rounded-md" />
          ) : badgeDist.length === 0 ? (
            <p className="text-slate-400 text-sm text-center py-6">No badge data available.</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-slate-200">
                    <th className="px-3 py-2 text-left text-xs font-semibold text-slate-500 uppercase tracking-wide">Badge</th>
                    <th className="px-3 py-2 text-left text-xs font-semibold text-slate-500 uppercase tracking-wide">Code</th>
                    <th className="px-3 py-2 text-right text-xs font-semibold text-slate-500 uppercase tracking-wide">Count Awarded</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {badgeDist.map((b) => (
                    <tr key={b.badge_code} className="hover:bg-slate-50">
                      <td className="px-3 py-2 font-medium text-slate-800">{b.badge_label || b.badge_code}</td>
                      <td className="px-3 py-2 text-xs text-slate-500 font-mono">{b.badge_code}</td>
                      <td className="px-3 py-2 text-right font-bold text-[#0F2847]">{(b.count || 0).toLocaleString()}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

        {/* Recompute action */}
        <div className="bg-white border border-slate-200 rounded-md p-6 flex items-center justify-between gap-4 flex-wrap">
          <div>
            <h3 className="font-semibold text-slate-900">Recompute Global Rankings</h3>
            <p className="text-sm text-slate-500 mt-1">
              Trigger a fresh ranking computation across all users. This may take a few minutes.
            </p>
          </div>
          <button
            onClick={handleComputeRankings}
            disabled={computing}
            className="flex-shrink-0 px-5 py-2.5 bg-[#0F2847] text-white text-sm font-semibold rounded-lg hover:bg-[#0F2847]/90 disabled:opacity-60 disabled:cursor-not-allowed transition-colors"
          >
            {computing ? "Computing…" : "Recompute Rankings"}
          </button>
        </div>
      </div>
    );
  };

  // ── Tab: Top Researchers ──────────────────────────────────────────────────

  const renderTop = () => {
    const isLoading = loading.top;
    return (
      <div className="bg-white border border-slate-200 rounded-md overflow-hidden">
        <div className="p-4 border-b border-slate-200 flex items-center justify-between">
          <h3 className="font-semibold text-slate-900">Top 50 Researchers</h3>
          <button onClick={fetchTop} className="text-xs text-slate-400 hover:text-slate-700 transition-colors">
            ↻ Refresh
          </button>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-200 bg-slate-50">
                <th className="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wide w-12">Rank</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wide">Name</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wide">Email</th>
                <th className="px-4 py-3 text-right text-xs font-semibold text-slate-500 uppercase tracking-wide">Score</th>
                <th className="px-4 py-3 text-center text-xs font-semibold text-slate-500 uppercase tracking-wide">Level</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wide">Institution</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wide">Country</th>
                <th className="px-4 py-3 text-center text-xs font-semibold text-slate-500 uppercase tracking-wide">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {isLoading
                ? Array.from({ length: 8 }).map((_, i) => (
                    <tr key={i}>
                      {[1,2,3,4,5,6,7,8].map((j) => (
                        <td key={j} className="px-4 py-3">
                          <SkeletonBlock className="h-4 w-full" />
                        </td>
                      ))}
                    </tr>
                  ))
                : topUsers.length === 0
                  ? (
                    <tr>
                      <td colSpan={8} className="text-center text-slate-400 py-12">No data available.</td>
                    </tr>
                  )
                  : topUsers.map((u, idx) => (
                    <tr key={u.user_id || idx} className="hover:bg-slate-50 transition-colors">
                      <td className="px-4 py-3 text-sm font-bold text-slate-500">#{idx + 1}</td>
                      <td className="px-4 py-3 font-medium text-slate-900">{u.full_name || "—"}</td>
                      <td className="px-4 py-3 text-slate-500 text-xs">{u.email || "—"}</td>
                      <td className="px-4 py-3 text-right font-bold text-[#0F2847]">
                        {(u.overall_score || 0).toLocaleString()}
                      </td>
                      <td className="px-4 py-3 text-center">
                        <LevelPill score={u.overall_score} />
                      </td>
                      <td className="px-4 py-3 text-slate-600 text-xs">{u.institution || "—"}</td>
                      <td className="px-4 py-3 text-slate-600 text-xs">{u.country || "—"}</td>
                      <td className="px-4 py-3 text-center">
                        <button
                          onClick={() => navigate(`/admin/users/${u.user_id}`)}
                          className="text-xs text-[#0F2847] font-medium hover:underline"
                        >
                          View Profile
                        </button>
                      </td>
                    </tr>
                  ))
              }
            </tbody>
          </table>
        </div>
      </div>
    );
  };

  // ── Tab: Fraud Alerts ─────────────────────────────────────────────────────

  const renderFraud = () => {
    const isLoading = loading.fraud;
    return (
      <div className="space-y-4">
        {/* Note */}
        <div className="bg-red-50 border border-red-200 rounded-md p-4 flex gap-3 items-start">
          <span className="text-red-600 text-lg flex-shrink-0 mt-0.5">🚨</span>
          <div>
            <p className="text-sm font-semibold text-red-800 mb-1">Fraud Detection Alerts</p>
            <p className="text-sm text-red-700">
              Users flagged for unusual activity patterns. Review their profiles for further investigation.
              Reputation scores cannot be manually adjusted — all values reflect verified activity.
            </p>
          </div>
        </div>

        <div className="bg-white border border-slate-200 rounded-md overflow-hidden">
          <div className="p-4 border-b border-slate-200 flex items-center justify-between">
            <h3 className="font-semibold text-slate-900">
              Flagged Users
              {fraudAlerts.length > 0 && (
                <span className="ml-2 text-xs font-normal text-red-600 bg-red-50 border border-red-200 px-2 py-0.5 rounded-full">
                  {fraudAlerts.length} alerts
                </span>
              )}
            </h3>
            <button onClick={fetchFraud} className="text-xs text-slate-400 hover:text-slate-700 transition-colors">
              ↻ Refresh
            </button>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-slate-200 bg-slate-50">
                  <th className="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wide">User</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wide">Email</th>
                  <th className="px-4 py-3 text-right text-xs font-semibold text-slate-500 uppercase tracking-wide">Events (7d)</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wide">Flag Reason</th>
                  <th className="px-4 py-3 text-center text-xs font-semibold text-slate-500 uppercase tracking-wide">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {isLoading
                  ? Array.from({ length: 5 }).map((_, i) => (
                      <tr key={i}>
                        {[1,2,3,4,5].map((j) => (
                          <td key={j} className="px-4 py-3">
                            <SkeletonBlock className="h-4 w-full" />
                          </td>
                        ))}
                      </tr>
                    ))
                  : fraudAlerts.length === 0
                    ? (
                      <tr>
                        <td colSpan={5} className="text-center text-slate-400 py-12">
                          No fraud alerts at this time.
                        </td>
                      </tr>
                    )
                    : fraudAlerts.map((alert, idx) => (
                      <tr key={alert.user_id || idx} className="hover:bg-red-50/30 transition-colors">
                        <td className="px-4 py-3 font-medium text-slate-900">
                          {alert.full_name || alert.user_id || "—"}
                        </td>
                        <td className="px-4 py-3 text-slate-500 text-xs">{alert.email || "—"}</td>
                        <td className="px-4 py-3 text-right">
                          <span className="font-bold text-red-600">{alert.total_events_7d ?? "—"}</span>
                        </td>
                        <td className="px-4 py-3">
                          <span className="text-xs text-red-700 bg-red-50 border border-red-100 px-2 py-1 rounded-lg">
                            {alert.flag_reason || "Unusual activity"}
                          </span>
                        </td>
                        <td className="px-4 py-3 text-center">
                          <button
                            onClick={() => navigate(`/admin/users/${alert.user_id}`)}
                            className="text-xs text-[#0F2847] font-medium hover:underline"
                          >
                            View Profile
                          </button>
                        </td>
                      </tr>
                    ))
                }
              </tbody>
            </table>
          </div>
        </div>
      </div>
    );
  };

  // ── Tab: Fastest Growing ──────────────────────────────────────────────────

  const renderFastest = () => {
    const isLoading = loading.fastest;
    return (
      <div className="bg-white border border-slate-200 rounded-md overflow-hidden">
        <div className="p-4 border-b border-slate-200 flex items-center justify-between">
          <div>
            <h3 className="font-semibold text-slate-900">Fastest Growing Researchers</h3>
            <p className="text-xs text-slate-500 mt-0.5">Top 20 by points gained in the last 30 days</p>
          </div>
          <button onClick={fetchFastest} className="text-xs text-slate-400 hover:text-slate-700 transition-colors">
            ↻ Refresh
          </button>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-200 bg-slate-50">
                <th className="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wide w-12">#</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wide">Name</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wide">Email</th>
                <th className="px-4 py-3 text-right text-xs font-semibold text-slate-500 uppercase tracking-wide">Current Score</th>
                <th className="px-4 py-3 text-right text-xs font-semibold text-slate-500 uppercase tracking-wide">+Points (30d)</th>
                <th className="px-4 py-3 text-center text-xs font-semibold text-slate-500 uppercase tracking-wide">Level</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wide">Institution</th>
                <th className="px-4 py-3 text-center text-xs font-semibold text-slate-500 uppercase tracking-wide">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {isLoading
                ? Array.from({ length: 8 }).map((_, i) => (
                    <tr key={i}>
                      {[1,2,3,4,5,6,7,8].map((j) => (
                        <td key={j} className="px-4 py-3">
                          <SkeletonBlock className="h-4 w-full" />
                        </td>
                      ))}
                    </tr>
                  ))
                : fastest.length === 0
                  ? (
                    <tr>
                      <td colSpan={8} className="text-center text-slate-400 py-12">No data available.</td>
                    </tr>
                  )
                  : fastest.map((u, idx) => (
                    <tr key={u.user_id || idx} className="hover:bg-slate-50 transition-colors">
                      <td className="px-4 py-3 text-sm font-bold text-slate-500">#{idx + 1}</td>
                      <td className="px-4 py-3 font-medium text-slate-900">{u.full_name || "—"}</td>
                      <td className="px-4 py-3 text-slate-500 text-xs">{u.email || "—"}</td>
                      <td className="px-4 py-3 text-right font-bold text-[#0F2847]">
                        {(u.overall_score || 0).toLocaleString()}
                      </td>
                      <td className="px-4 py-3 text-right">
                        <span className="font-bold text-emerald-600">
                          +{(u.points_gained_30d || u.points_30d || 0).toLocaleString()}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-center">
                        <LevelPill score={u.overall_score} />
                      </td>
                      <td className="px-4 py-3 text-slate-600 text-xs">{u.institution || "—"}</td>
                      <td className="px-4 py-3 text-center">
                        <button
                          onClick={() => navigate(`/admin/users/${u.user_id}`)}
                          className="text-xs text-[#0F2847] font-medium hover:underline"
                        >
                          View Profile
                        </button>
                      </td>
                    </tr>
                  ))
              }
            </tbody>
          </table>
        </div>
      </div>
    );
  };

  // ── Render ────────────────────────────────────────────────────────────────

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
        <div className="flex gap-1 bg-white border border-slate-200 rounded-md p-1 mb-6 overflow-x-auto">
          {TABS.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex-shrink-0 py-2 px-4 rounded-lg text-sm font-medium transition-colors whitespace-nowrap ${
                activeTab === tab.id
                  ? "bg-[#0F2847] text-white"
                  : "text-slate-600 hover:bg-slate-100"
              }`}
            >
              {tab.label}
              {tab.id === "fraud" && fraudAlerts.length > 0 && (
                <span className="ml-2 text-xs bg-red-500 text-white px-1.5 py-0.5 rounded-full">
                  {fraudAlerts.length}
                </span>
              )}
            </button>
          ))}
        </div>

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
