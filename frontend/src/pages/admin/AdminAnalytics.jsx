import React, { useState, useEffect } from "react";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell, PieChart, Pie, Legend } from "recharts";
import api from "@/lib/api";
import { SkeletonPage } from "@/components/ds/LoadingState";
import { ErrorState } from "@/components/ds/ErrorState";
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

  return (
    <AdministrationLayout
      title="Platform Analytics"
      subtitle="Derived from real platform activity"
    >
      {/* Plan Distribution */}
      {planChartData.length > 0 && (
        <div className="bg-white border border-slate-200 p-5">
          <h2 className="text-xs font-semibold uppercase tracking-widest text-slate-500 mb-4">Plan Distribution</h2>
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
        </div>
      )}

      {/* Engagement */}
      {Object.keys(engagement).length > 0 && (
        <div className="bg-white border border-slate-200 p-5">
          <h2 className="text-xs font-semibold uppercase tracking-widest text-slate-500 mb-4">Engagement Overview</h2>
          <div className="grid grid-cols-3 gap-4">
            {Object.entries(engagement).filter(([k]) => k !== "plan_distribution").map(([key, value]) => (
              <div key={key} className="bg-slate-50 border border-slate-200 px-4 py-3 text-center">
                <div className="font-serif text-2xl text-slate-900">{typeof value === "number" ? value.toLocaleString() : String(value)}</div>
                <div className="text-xs text-slate-500 mt-0.5">{key.replace(/_/g, " ")}</div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Feature Adoption */}
      {Object.keys(featureAdoption).length > 0 && (
        <div className="bg-white border border-slate-200 p-5">
          <h2 className="text-xs font-semibold uppercase tracking-widest text-slate-500 mb-4">Feature Adoption</h2>
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-200">
                <th className="text-left py-2 text-xs font-semibold uppercase tracking-widest text-slate-500">Feature</th>
                <th className="text-right py-2 text-xs font-semibold uppercase tracking-widest text-slate-500">Usage</th>
              </tr>
            </thead>
            <tbody>
              {Object.entries(featureAdoption).map(([key, value]) => (
                <tr key={key} className="border-b border-slate-100">
                  <td className="py-2.5 text-slate-700 capitalize">{key.replace(/_/g, " ")}</td>
                  <td className="py-2.5 text-right font-medium text-slate-900">{typeof value === "number" ? value.toLocaleString() : String(value)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </AdministrationLayout>
  );
}
