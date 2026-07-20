import React, { useState, useEffect } from "react";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from "recharts";
import { Users, DollarSign, Activity, Server } from "lucide-react";
import api from "@/lib/api";
import { NAVY } from "@/lib/tokens";
import { SkeletonPage } from "@/components/ds/LoadingState";
import { ErrorState } from "@/components/ds/ErrorState";
import { AdministrationLayout } from "@/layouts";

function KpiCard({ label, value, sub, icon: Icon, iconColor = "text-slate-600" }) {
  return (
    <div className="bg-white border border-slate-200 p-5">
      <div className="flex items-start justify-between">
        <div>
          <p className="text-xs font-semibold uppercase tracking-widest text-slate-500">{label}</p>
          <p className="font-serif text-3xl text-slate-900 mt-1">{value}</p>
          {sub && <p className="text-xs text-slate-500 mt-1">{sub}</p>}
        </div>
        <Icon size={20} className={iconColor} />
      </div>
    </div>
  );
}

function MetricRow({ label, value }) {
  return (
    <div className="flex justify-between items-center py-2 border-b border-slate-100 last:border-0">
      <span className="text-sm text-slate-600">{label}</span>
      <span className="text-sm font-medium text-slate-900">{value?.toLocaleString() ?? "—"}</span>
    </div>
  );
}

function StatusDot({ ok }) {
  return (
    <span className={`inline-block w-2 h-2 rounded-full mr-2 ${ok ? "bg-green-500" : "bg-red-500"}`} />
  );
}

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

  return (
    <AdministrationLayout
      title="Admin Dashboard"
      subtitle="Platform overview — live data"
    >
      {/* KPI Row */}
      <div className="grid grid-cols-4 gap-4">
        <KpiCard
          label="Total Users"
          value={users.total.toLocaleString()}
          sub={`+${users.new_today} today · +${users.new_week} this week`}
          icon={Users}
          iconColor="text-blue-600"
        />
        <KpiCard
          label="Active Subscribers"
          value={financial.active_subscribers.toLocaleString()}
          sub={`${financial.churn_rate_pct}% churn (30d)`}
          icon={Users}
          iconColor="text-indigo-600"
        />
        <KpiCard
          label="Monthly Revenue"
          value={`€${financial.mrr_eur.toFixed(2)}`}
          sub={`ARR €${financial.arr_eur.toFixed(2)}`}
          icon={DollarSign}
          iconColor="text-green-600"
        />
        <KpiCard
          label="System Status"
          value={systemIssues === 0 ? "Operational" : `${systemIssues} issue${systemIssues > 1 ? "s" : ""}`}
          sub={systemIssues === 0 ? "All systems nominal" : "Check health page"}
          icon={Activity}
          iconColor={systemIssues === 0 ? "text-green-600" : "text-red-600"}
        />
      </div>

      {/* Metrics grid */}
      <div className="grid grid-cols-3 gap-4">
        {/* Users breakdown */}
        <div className="bg-white border border-slate-200 p-5">
          <h2 className="text-xs font-semibold uppercase tracking-widest text-slate-500 mb-3">Users by Plan</h2>
          <MetricRow label="Free" value={users.free} />
          <MetricRow label="Researcher" value={users.researcher} />
          <MetricRow label="Pro Researcher" value={users.pro_researcher} />
          <MetricRow label="Institution" value={users.institution} />
          <MetricRow label="ORCID Connected" value={users.orcid_connected} />
          <MetricRow label="Email Verified" value={users.email_verified} />
          {(users.suspended > 0 || users.banned > 0) && (
            <>
              <MetricRow label="Suspended" value={users.suspended} />
              <MetricRow label="Banned" value={users.banned} />
            </>
          )}
        </div>

        {/* Engagement */}
        <div className="bg-white border border-slate-200 p-5">
          <h2 className="text-xs font-semibold uppercase tracking-widest text-slate-500 mb-3">Engagement (30d)</h2>
          <MetricRow label="Projects Created" value={engagement.projects_month} />
          <MetricRow label="Workspaces Created" value={engagement.workspaces_month} />
          <MetricRow label="Active Collaborations" value={engagement.collaborations_active} />
          <MetricRow label="Manuscripts" value={engagement.manuscripts_total} />
          <MetricRow label="AI Requests" value={engagement.ai_requests_month} />
          <MetricRow label="Messages Sent" value={engagement.messages_month} />
        </div>

        {/* Research chart */}
        <div className="bg-white border border-slate-200 p-5">
          <h2 className="text-xs font-semibold uppercase tracking-widest text-slate-500 mb-3">AI Research Tools (30d)</h2>
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
        </div>
      </div>

      {/* Financial + System */}
      <div className="grid grid-cols-2 gap-4">
        <div className="bg-white border border-slate-200 p-5">
          <h2 className="text-xs font-semibold uppercase tracking-widest text-slate-500 mb-3">Financial (30d)</h2>
          <MetricRow label="Pack Revenue" value={`€${financial.pack_revenue_30d_eur.toFixed(2)}`} />
          <MetricRow label="Credits Consumed" value={financial.credits_consumed_30d.toLocaleString()} />
          <MetricRow label="Credits Purchased" value={financial.credits_purchased_30d.toLocaleString()} />
          <MetricRow label="Churned Users" value={financial.churned_30d} />
          <MetricRow label="Churn Rate" value={`${financial.churn_rate_pct}%`} />
        </div>

        <div className="bg-white border border-slate-200 p-5">
          <h2 className="text-xs font-semibold uppercase tracking-widest text-slate-500 mb-3">System Health</h2>
          <table className="w-full text-sm">
            <tbody>
              {systemChecks.map(({ label, ok }) => (
                <tr key={label} className="border-b border-slate-100 last:border-0">
                  <td className="py-2 text-slate-600">{label}</td>
                  <td className="py-2 text-right">
                    <StatusDot ok={ok} />
                    <span className={ok ? "text-green-700" : "text-red-700"}>
                      {ok ? "Configured" : "Not configured"}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </AdministrationLayout>
  );
}
