import React, { useState, useEffect } from "react";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from "recharts";
import { Users, DollarSign, Activity, Server } from "lucide-react";
import api from "@/lib/api";
import { NAVY } from "@/lib/tokens";
import { SkeletonPage } from "@/components/ds/LoadingState";
import { ErrorState } from "@/components/ds/ErrorState";
import { Card, H2, List, ListItem, StatusDot, DataTable } from "@/components/ds";
import { AdministrationLayout } from "@/layouts";

export default function AdminDashboard() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    api.get("/admin/dashboard")
      .then((r) => setData(r.data))
      .catch((e) => setError(e.response?.data?.detail || "Failed to load dashboard"))
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return <div className="p-8"><SkeletonPage /></div>;
  }

  if (error) {
    return (
      <div className="p-8">
        <ErrorState message={error} type="server" onRetry={() => api.get("/admin/dashboard").then((r) => setData(r.data)).catch((e) => setError(e.response?.data?.detail || "Failed to load dashboard"))} />
      </div>
    );
  }

  const { users, engagement, research, financial, system } = data;

  const systemIssues = Object.values(system).filter((v) => !v).length;

  const researchChartData = [
    { name: "Literature", value: research.literature_reviews_month },
    { name: "Gap Analysis", value: research.gap_reviews_month },
    { name: "Manuscript", value: research.manuscript_reviews_month },
    { name: "Statistical", value: research.stat_reviews_month },
    { name: "Design", value: research.design_reviews_month },
  ];

  const CHART_COLORS = ["#0F2847", "#1e3a5f", "#2d5080", "#3b6aa0", "#4a84c0"];

  const systemChecks = [
    { label: "Database", ok: system.db_ok },
    { label: "Email Service", ok: system.email_configured },
    { label: "ORCID OAuth", ok: system.orcid_configured },
    { label: "Stripe Payments", ok: system.stripe_configured },
  ];

  const systemColumns = [
    { key: "label", label: "Check", render: (v) => <span className="text-slate-600">{v}</span> },
    {
      key: "ok",
      label: "Status",
      align: "right",
      render: (ok) => (
        <span className="inline-flex items-center justify-end gap-2">
          <StatusDot color={ok ? "#16a34a" : "#dc2626"} size={8} />
          <span className={ok ? "text-green-700" : "text-red-700"}>
            {ok ? "Configured" : "Not configured"}
          </span>
        </span>
      ),
    },
  ];

  return (
    <AdministrationLayout
      title="Admin Dashboard"
      subtitle="Platform overview — live data"
      stats={[
        { label: "Total Users", value: users.total.toLocaleString() },
        { label: "Active Subscribers", value: financial.active_subscribers.toLocaleString() },
        { label: "Monthly Revenue", value: `€${financial.mrr_eur.toFixed(2)}` },
        { label: "System Status", value: systemIssues === 0 ? "Operational" : `${systemIssues} issue${systemIssues > 1 ? "s" : ""}` },
      ]}
      sidebar={<DashboardSidebar users={users} financial={financial} />}
    >
      {/* Metrics grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 mt-4">
        {/* Users breakdown */}
        <Card padding="lg">
          <H2 className="text-xs font-semibold uppercase tracking-widest text-slate-500 mb-3">Users by Plan</H2>
          <List radius={0} border={false}>
            <ListItem compact title="Free" trailing={users.free?.toLocaleString() ?? "—"} style={{ padding: "8px 0" }} />
            <ListItem compact title="Researcher" trailing={users.researcher?.toLocaleString() ?? "—"} style={{ padding: "8px 0" }} />
            <ListItem compact title="Pro Researcher" trailing={users.pro_researcher?.toLocaleString() ?? "—"} style={{ padding: "8px 0" }} />
            <ListItem compact title="Institution" trailing={users.institution?.toLocaleString() ?? "—"} style={{ padding: "8px 0" }} />
            <ListItem compact title="ORCID Connected" trailing={users.orcid_connected?.toLocaleString() ?? "—"} style={{ padding: "8px 0" }} />
            <ListItem
              compact
              title="Email Verified"
              trailing={users.email_verified?.toLocaleString() ?? "—"}
              style={{ padding: "8px 0", borderBottom: (users.suspended > 0 || users.banned > 0) ? undefined : "none" }}
            />
            {(users.suspended > 0 || users.banned > 0) && (
              <>
                <ListItem compact title="Suspended" trailing={users.suspended?.toLocaleString() ?? "—"} style={{ padding: "8px 0" }} />
                <ListItem compact title="Banned" trailing={users.banned?.toLocaleString() ?? "—"} style={{ padding: "8px 0", borderBottom: "none" }} />
              </>
            )}
          </List>
        </Card>

        {/* Engagement */}
        <Card padding="lg">
          <H2 className="text-xs font-semibold uppercase tracking-widest text-slate-500 mb-3">Engagement (30d)</H2>
          <List radius={0} border={false}>
            <ListItem compact title="Projects Created" trailing={engagement.projects_month?.toLocaleString() ?? "—"} style={{ padding: "8px 0" }} />
            <ListItem compact title="Workspaces Created" trailing={engagement.workspaces_month?.toLocaleString() ?? "—"} style={{ padding: "8px 0" }} />
            <ListItem compact title="Active Collaborations" trailing={engagement.collaborations_active?.toLocaleString() ?? "—"} style={{ padding: "8px 0" }} />
            <ListItem compact title="Manuscripts" trailing={engagement.manuscripts_total?.toLocaleString() ?? "—"} style={{ padding: "8px 0" }} />
            <ListItem compact title="AI Requests" trailing={engagement.ai_requests_month?.toLocaleString() ?? "—"} style={{ padding: "8px 0" }} />
            <ListItem compact title="Messages Sent" trailing={engagement.messages_month?.toLocaleString() ?? "—"} style={{ padding: "8px 0", borderBottom: "none" }} />
          </List>
        </Card>

        {/* Research chart */}
        <Card padding="lg">
          <H2 className="text-xs font-semibold uppercase tracking-widest text-slate-500 mb-3">AI Research Tools (30d)</H2>
          <ResponsiveContainer width="100%" height={140}>
            <BarChart data={researchChartData} barSize={18}>
              <XAxis dataKey="name" tick={{ fontSize: 10 }} />
              <YAxis tick={{ fontSize: 10 }} />
              <Tooltip />
              <Bar dataKey="value" radius={0}>
                {researchChartData.map((_, i) => (
                  <Cell key={i} fill={CHART_COLORS[i % CHART_COLORS.length]} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </Card>
      </div>

      {/* Financial + System */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-4">
        <Card padding="lg">
          <H2 className="text-xs font-semibold uppercase tracking-widest text-slate-500 mb-3">Financial (30d)</H2>
          <List radius={0} border={false}>
            <ListItem compact title="Pack Revenue" trailing={`€${financial.pack_revenue_30d_eur.toFixed(2)}`} style={{ padding: "8px 0" }} />
            <ListItem compact title="Credits Consumed" trailing={financial.credits_consumed_30d.toLocaleString()} style={{ padding: "8px 0" }} />
            <ListItem compact title="Credits Purchased" trailing={financial.credits_purchased_30d.toLocaleString()} style={{ padding: "8px 0" }} />
            <ListItem compact title="Churned Users" trailing={financial.churned_30d?.toLocaleString() ?? "—"} style={{ padding: "8px 0" }} />
            <ListItem compact title="Churn Rate" trailing={`${financial.churn_rate_pct}%`} style={{ padding: "8px 0", borderBottom: "none" }} />
          </List>
        </Card>

        <Card padding="lg">
          <H2 className="text-xs font-semibold uppercase tracking-widest text-slate-500 mb-3">System Health</H2>
          <DataTable columns={systemColumns} rows={systemChecks} />
        </Card>
      </div>
    </AdministrationLayout>
  );
}

// ── Right rail — growth and revenue detail dropped from the hero ribbon,
// pulled from the same /admin/dashboard payload already fetched above ────────
function DashboardSidebar({ users, financial }) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      <Card padding="lg">
        <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 8 }}>
          <Users size={13} style={{ color: NAVY }} />
          <div style={{ fontSize: 13, fontWeight: 700, color: "#0f172a" }}>Growth Snapshot</div>
        </div>
        <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
          <div style={{ display: "flex", justifyContent: "space-between", fontSize: 12, color: "#374151" }}>
            <span>New today</span>
            <span style={{ fontWeight: 700 }}>{users.new_today}</span>
          </div>
          <div style={{ display: "flex", justifyContent: "space-between", fontSize: 12, color: "#374151" }}>
            <span>New this week</span>
            <span style={{ fontWeight: 700 }}>{users.new_week}</span>
          </div>
          <div style={{ display: "flex", justifyContent: "space-between", fontSize: 12, color: "#374151" }}>
            <span>Churn (30d)</span>
            <span style={{ fontWeight: 700 }}>{financial.churn_rate_pct}%</span>
          </div>
        </div>
      </Card>

      <Card padding="lg">
        <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 8 }}>
          <DollarSign size={13} style={{ color: NAVY }} />
          <div style={{ fontSize: 13, fontWeight: 700, color: "#0f172a" }}>Annual Revenue</div>
        </div>
        <div style={{ fontFamily: "Georgia, serif", fontSize: 24, color: "#0f172a" }}>€{financial.arr_eur.toFixed(2)}</div>
        <p style={{ fontSize: 12, color: "#64748B", margin: "4px 0 0" }}>Recurring revenue, annualized</p>
      </Card>
    </div>
  );
}
