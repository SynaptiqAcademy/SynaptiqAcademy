import React, { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { ResponsiveContainer, Cell, PieChart, Pie, Tooltip } from "recharts";
import { TrendingUp, Users, MousePointerClick, Repeat, Building2, Gift } from "lucide-react";
import api from "@/lib/api";
import { SkeletonPage } from "@/components/ds/LoadingState";
import { ErrorState } from "@/components/ds/ErrorState";
import { EmptyState } from "@/components/ds/EmptyState";
import { Card, DataTable, H2, Badge } from "@/components/ds";
import { NAVY } from "@/lib/tokens";
import { AdministrationLayout } from "@/layouts";

const PLAN_COLORS = { free: "#94a3b8", researcher: "#3b82f6", pro_researcher: "#6366f1", institution: "#a855f7" };

function planBadgeVariant(plan) {
  if (plan === "institution") return "purple";
  if (plan === "pro_researcher" || plan === "researcher") return "info";
  return "neutral";
}

export default function AdminAnalytics() {
  const navigate = useNavigate();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    api.get("/admin/analytics")
      .then((r) => setData(r.data))
      .catch((e) => setError(e.response?.data?.detail || "Failed to load analytics"))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="p-8"><SkeletonPage /></div>;
  if (error) return <div className="p-8"><ErrorState message={error} type="server" /></div>;
  if (!data) return null;

  // Every field below is read straight off services/engagement.py's
  // platform_analytics() response — no fabricated shape, no placeholder rows.
  const activeUsers = data.active_users || {};
  const sessions = data.sessions || {};
  const topPages = data.top_pages || [];
  const featureUsage = data.feature_usage || [];
  const topUsers = data.top_users || [];
  const topInstitutions = data.top_institutions || [];
  const planDist = data.plan_distribution || {};
  const referrals = data.referrals || {};

  const planChartData = Object.entries(planDist).map(([name, value]) => ({ name, value }));
  const maxPageViews = Math.max(1, ...topPages.map((p) => p.views));

  const stats = [
    { label: "Daily Active", value: (activeUsers.dau ?? 0).toLocaleString() },
    { label: "Weekly Active", value: (activeUsers.wau ?? 0).toLocaleString() },
    { label: "Monthly Active", value: (activeUsers.mau ?? 0).toLocaleString() },
    { label: "Retention (7d)", value: `${data.retention_pct ?? 0}%` },
    { label: "Avg Session", value: `${sessions.avg_session_minutes ?? 0} min` },
  ];

  const featureColumns = [
    {
      key: "action",
      label: "Feature",
      render: (v) => <span className="capitalize text-slate-700">{String(v).replace(/_/g, " ")}</span>,
    },
    { key: "uses", label: "Uses", align: "right", render: (v) => <span className="font-medium text-slate-900">{v.toLocaleString()}</span> },
    { key: "credits", label: "Credits Spent", align: "right", render: (v) => <span className="text-slate-500">{v.toLocaleString()}</span> },
  ];

  const userColumns = [
    {
      key: "full_name",
      label: "User",
      render: (v, row) => (
        <div>
          <div className="text-slate-900 font-medium">{v}</div>
          <div className="text-xs text-slate-400">{row.email}</div>
        </div>
      ),
    },
    { key: "plan_code", label: "Plan", render: (v) => <Badge variant={planBadgeVariant(v)}>{(v || "free").replace("_", " ")}</Badge> },
    { key: "sessions", label: "Sessions (30d)", align: "right", render: (v) => <span className="font-medium text-slate-900">{v}</span> },
  ];

  const instColumns = [
    { key: "institution_id", label: "Institution" },
    { key: "users", label: "Users", align: "right", render: (v) => <span className="font-medium text-slate-900">{v}</span> },
  ];

  return (
    <AdministrationLayout
      title="Platform Analytics"
      subtitle="Real usage — who's active, what they use, where they spend time"
      stats={stats}
      sidebar={
        <AnalyticsSidebar
          referrals={referrals}
          sessions30d={sessions.sessions_30d ?? 0}
          topFeature={featureUsage[0]}
        />
      }
    >
      {/* Plan Distribution */}
      {planChartData.length > 0 && (
        <Card padding="lg">
          <H2 className="text-xs font-semibold uppercase tracking-widest text-slate-500 mb-4">Plan Distribution</H2>
          <div className="flex gap-8 items-center flex-wrap">
            <ResponsiveContainer width={200} height={200}>
              <PieChart>
                <Pie data={planChartData} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={80}>
                  {planChartData.map((entry) => (
                    <Cell key={entry.name} fill={PLAN_COLORS[entry.name] || "#94a3b8"} />
                  ))}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
            <div className="space-y-2">
              {planChartData.map((entry) => (
                <div key={entry.name} className="flex items-center gap-3">
                  <div className="w-3 h-3 flex-shrink-0" style={{ backgroundColor: PLAN_COLORS[entry.name] || "#94a3b8" }} />
                  <span className="text-sm text-slate-700 capitalize">{entry.name?.replace("_", " ")}</span>
                  <span className="text-sm font-medium text-slate-900 ml-auto">{entry.value?.toLocaleString()}</span>
                </div>
              ))}
            </div>
          </div>
        </Card>
      )}

      {/* Most Accessed Pages */}
      <Card padding="lg">
        <div className="flex items-center gap-2 mb-4">
          <MousePointerClick size={14} className="text-slate-400" />
          <H2 className="text-xs font-semibold uppercase tracking-widest text-slate-500 m-0">Most Accessed Pages (30d)</H2>
        </div>
        {topPages.length === 0 ? (
          <EmptyState title="No page views yet" description="Data appears here as users navigate the app." />
        ) : (
          <div className="space-y-2.5">
            {topPages.map((p) => (
              <div key={p.path} className="flex items-center gap-3">
                <span className="text-sm text-slate-700 font-mono w-40 truncate flex-shrink-0">{p.path}</span>
                <div className="flex-1 h-2 bg-slate-100 rounded-full overflow-hidden">
                  <div
                    className="h-full rounded-full"
                    style={{ width: `${(p.views / maxPageViews) * 100}%`, background: NAVY }}
                  />
                </div>
                <span className="text-sm font-medium text-slate-900 w-12 text-right flex-shrink-0">{p.views}</span>
              </div>
            ))}
          </div>
        )}
      </Card>

      {/* Feature Adoption (from real credit-billed AI usage) */}
      <Card padding="lg">
        <H2 className="text-xs font-semibold uppercase tracking-widest text-slate-500 mb-4">Most Used Features (30d)</H2>
        {featureUsage.length === 0 ? (
          <EmptyState title="No feature usage yet" description="Populated from real credit-billed AI actions." />
        ) : (
          <DataTable columns={featureColumns} rows={featureUsage} />
        )}
      </Card>

      {/* Most Active Users */}
      <Card padding="lg">
        <div className="flex items-center gap-2 mb-4">
          <Users size={14} className="text-slate-400" />
          <H2 className="text-xs font-semibold uppercase tracking-widest text-slate-500 m-0">Most Active Users (30d)</H2>
        </div>
        {topUsers.length === 0 ? (
          <EmptyState title="No active users yet" />
        ) : (
          <DataTable columns={userColumns} rows={topUsers} onRowClick={(row) => navigate(`/admin/users/${row.user_id}`)} />
        )}
      </Card>

      {/* Top Institutions */}
      {topInstitutions.length > 0 && (
        <Card padding="lg">
          <div className="flex items-center gap-2 mb-4">
            <Building2 size={14} className="text-slate-400" />
            <H2 className="text-xs font-semibold uppercase tracking-widest text-slate-500 m-0">Most Active Institutions</H2>
          </div>
          <DataTable columns={instColumns} rows={topInstitutions} />
        </Card>
      )}
    </AdministrationLayout>
  );
}

// ── Right rail — derived from data already fetched above, never fabricated ────
function AnalyticsSidebar({ referrals, sessions30d, topFeature }) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      <Card padding="lg">
        <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 8 }}>
          <Repeat size={13} style={{ color: NAVY }} />
          <div style={{ fontSize: 13, fontWeight: 700, color: "#0f172a" }}>Sessions (30d)</div>
        </div>
        <div style={{ fontFamily: "Georgia, serif", fontSize: 24, color: "#0f172a" }}>
          {(sessions30d ?? 0).toLocaleString()}
        </div>
      </Card>

      {topFeature && (
        <Card padding="lg">
          <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 8 }}>
            <TrendingUp size={13} style={{ color: NAVY }} />
            <div style={{ fontSize: 13, fontWeight: 700, color: "#0f172a" }}>Most-Used Feature</div>
          </div>
          <div style={{ fontFamily: "Georgia, serif", fontSize: 16, color: "#0f172a", textTransform: "capitalize" }}>
            {String(topFeature.action).replace(/_/g, " ")}
          </div>
          <p style={{ fontSize: 12, color: "#64748B", margin: "6px 0 0" }}>
            {topFeature.uses?.toLocaleString()} uses
          </p>
        </Card>
      )}

      <Card padding="lg">
        <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 8 }}>
          <Gift size={13} style={{ color: NAVY }} />
          <div style={{ fontSize: 13, fontWeight: 700, color: "#0f172a" }}>Referrals</div>
        </div>
        <div style={{ fontFamily: "Georgia, serif", fontSize: 20, color: "#0f172a" }}>
          {(referrals.total ?? 0).toLocaleString()}
        </div>
        <p style={{ fontSize: 12, color: "#64748B", margin: "6px 0 0" }}>
          {(referrals.qualified ?? 0).toLocaleString()} qualified
        </p>
      </Card>
    </div>
  );
}
