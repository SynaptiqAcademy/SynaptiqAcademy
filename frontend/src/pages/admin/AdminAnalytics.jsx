import React, { useState, useEffect } from "react";
import { ResponsiveContainer, Cell, PieChart, Pie, Tooltip } from "recharts";
import { TrendingUp, Sparkles } from "lucide-react";
import api from "@/lib/api";
import { SkeletonPage } from "@/components/ds/LoadingState";
import { ErrorState } from "@/components/ds/ErrorState";
import { Card, DataTable, H2 } from "@/components/ds";
import { NAVY } from "@/lib/tokens";
import { AdministrationLayout } from "@/layouts";

const PLAN_COLORS = { free: "#94a3b8", researcher: "#3b82f6", pro_researcher: "#6366f1", institution: "#a855f7" };

export default function AdminAnalytics() {
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

  // Build plan distribution from engagement_overview or directly
  const planDist = data.engagement_overview?.plan_distribution || data.plan_distribution || {};
  const planChartData = Object.entries(planDist).map(([name, value]) => ({ name, value }));

  const engagement = data.engagement_overview || {};
  const featureAdoption = data.feature_adoption || {};

  const featureColumns = [
    {
      key: "feature",
      label: "Feature",
      render: (v) => <span className="capitalize text-slate-700">{v.replace(/_/g, " ")}</span>,
    },
    {
      key: "usage",
      label: "Usage",
      align: "right",
      render: (v) => <span className="font-medium text-slate-900">{typeof v === "number" ? v.toLocaleString() : String(v)}</span>,
    },
  ];
  const featureRows = Object.entries(featureAdoption).map(([key, value]) => ({ feature: key, usage: value }));

  const engagementStats = Object.entries(engagement)
    .filter(([k]) => k !== "plan_distribution")
    .map(([key, value]) => ({
      label: key.replace(/_/g, " "),
      value: typeof value === "number" ? value.toLocaleString() : String(value),
    }));

  const topPlan = planChartData.length > 0
    ? planChartData.reduce((a, b) => (b.value > a.value ? b : a))
    : null;
  const topFeature = featureRows.length > 0
    ? featureRows.reduce((a, b) => (b.usage > a.usage ? b : a))
    : null;

  return (
    <AdministrationLayout
      title="Platform Analytics"
      subtitle="Derived from real platform activity"
      stats={engagementStats.length > 0 ? engagementStats : undefined}
      sidebar={(topPlan || topFeature) ? <AnalyticsSidebar topPlan={topPlan} topFeature={topFeature} /> : undefined}
    >
      {/* Plan Distribution */}
      {planChartData.length > 0 && (
        <Card padding="lg">
          <H2 className="text-xs font-semibold uppercase tracking-widest text-slate-500 mb-4">Plan Distribution</H2>
          <div className="flex gap-8 items-center">
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

      {/* Feature Adoption */}
      {Object.keys(featureAdoption).length > 0 && (
        <Card padding="lg" className="mt-4">
          <H2 className="text-xs font-semibold uppercase tracking-widest text-slate-500 mb-4">Feature Adoption</H2>
          <DataTable columns={featureColumns} rows={featureRows} />
        </Card>
      )}
    </AdministrationLayout>
  );
}

// ── Right rail — derived from data already fetched above, never fabricated ────
function AnalyticsSidebar({ topPlan, topFeature }) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      {topPlan && (
        <Card padding="lg">
          <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 8 }}>
            <Sparkles size={13} style={{ color: NAVY }} />
            <div style={{ fontSize: 13, fontWeight: 700, color: "#0f172a" }}>Leading Plan</div>
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <div className="w-3 h-3 flex-shrink-0" style={{ background: PLAN_COLORS[topPlan.name] || "#94a3b8" }} />
            <div style={{ fontFamily: "Georgia, serif", fontSize: 20, color: "#0f172a", textTransform: "capitalize" }}>{topPlan.name?.replace("_", " ")}</div>
          </div>
          <p style={{ fontSize: 12, color: "#64748B", margin: "6px 0 0" }}>
            {topPlan.value?.toLocaleString()} user{topPlan.value !== 1 ? "s" : ""} on this plan
          </p>
        </Card>
      )}

      {topFeature && (
        <Card padding="lg">
          <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 8 }}>
            <TrendingUp size={13} style={{ color: NAVY }} />
            <div style={{ fontSize: 13, fontWeight: 700, color: "#0f172a" }}>Most-Used Feature</div>
          </div>
          <div style={{ fontFamily: "Georgia, serif", fontSize: 16, color: "#0f172a", textTransform: "capitalize" }}>
            {topFeature.feature?.replace(/_/g, " ")}
          </div>
          <p style={{ fontSize: 12, color: "#64748B", margin: "6px 0 0" }}>
            {typeof topFeature.usage === "number" ? topFeature.usage.toLocaleString() : topFeature.usage} uses
          </p>
        </Card>
      )}
    </div>
  );
}
