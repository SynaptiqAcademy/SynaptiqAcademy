import React, { useState, useCallback, useEffect } from "react";
import {
  AreaChart, Area, BarChart, Bar, LineChart, Line,
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend,
} from "recharts";
import { DollarSign, TrendingUp, TrendingDown, Users, RefreshCw } from "lucide-react";
import api from "@/lib/api";
import { NAVY } from "@/lib/tokens";
import { AdministrationLayout } from "@/layouts";
import { Card, Button, FormSelect, StatCard, StatGrid, ProgressBar } from "@/components/ds";

function useAOS(path, params = {}) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const query = new URLSearchParams(params).toString();
  const fetch = useCallback(() => {
    setLoading(true);
    api.get(`/admin/aos/${path}${query ? "?" + query : ""}`)
      .then((r) => setData(r.data))
      .catch(() => setData(null))
      .finally(() => setLoading(false));
  }, [path, query]);
  useEffect(() => { fetch(); }, [fetch]);
  return { data, loading, refetch: fetch };
}

const CHART_OPTS = { contentStyle: { backgroundColor: "#ffffff", border: "1px solid #e2e8f0", fontSize: 12 } };

export default function AdminRevenuePage() {
  const [days, setDays] = useState(30);
  const { data: metrics, loading: mLoad, refetch: refMetrics } = useAOS("revenue/metrics", { days });
  const { data: byCountry, loading: cLoad, refetch: refCountry } = useAOS("revenue/by-country");
  const { data: forecast, loading: fLoad, refetch: refForecast } = useAOS("revenue/forecast");
  const loading = mLoad || cLoad || fLoad;

  const m = metrics || {};
  const fc = forecast || {};
  const chartData = [...(fc.history || []), ...(fc.forecast || []).map((d) => ({ ...d, revenue_eur: null, projected_eur: d.projected_eur }))];

  return (
    <AdministrationLayout
      title="Financial Control Center"
      subtitle="MRR · ARR · ARPU · LTV · CAC · Conversion · Retention · By-Country"
      actions={
        <div className="flex items-center gap-2">
          <FormSelect
            value={days}
            onChange={(e) => setDays(Number(e.target.value))}
            wrapperClassName="!mb-0"
            size="sm"
          >
            <option value={30}>30 days</option>
            <option value={60}>60 days</option>
            <option value={90}>90 days</option>
          </FormSelect>
          <Button
            variant="hero"
            size="icon"
            onClick={() => { refMetrics(); refCountry(); refForecast(); }}
            aria-label="Refresh"
          >
            <RefreshCw size={14} className={loading ? "animate-spin" : ""} />
          </Button>
        </div>
      }
    >
      <div className="flex flex-col gap-6">
        {/* Primary KPIs */}
        {!mLoad && (
          <>
            <StatGrid cols={4}>
              <StatCard icon={<DollarSign />} label="MRR (EUR)" value={`€${m.mrr_eur?.toLocaleString()}`} highlight />
              <StatCard icon={<TrendingUp />} label="ARR (EUR)" value={`€${m.arr_eur?.toLocaleString()}`} highlight />
              <StatCard icon={<DollarSign />} label="ARPU (EUR)" value={`€${m.arpu_eur}`} sub="per active subscriber" />
              <StatCard icon={<TrendingUp />} label="LTV (EUR)" value={m.ltv_eur ? `€${m.ltv_eur}` : "N/A"} sub="ARPU ÷ churn rate" />
            </StatGrid>
            <StatGrid cols={4}>
              <StatCard icon={<DollarSign />} label="CAC (EUR)" value={m.cac_eur ? `€${m.cac_eur}` : "N/A"} sub="estimated cost per acquisition" />
              <StatCard icon={<Users />} label="Active Subscribers" value={m.active_subscribers?.toLocaleString()} sub={`of ${m.total_users?.toLocaleString()} total users`} />
              <StatCard icon={<TrendingDown />} label="Churn Rate" value={`${m.churn_rate_pct ?? 0}%`} sub={`${m.churned_period ?? 0} churned in ${days}d`} />
              <StatCard icon={<TrendingUp />} label="Retention Rate" value={`${m.retention_rate_pct ?? 0}%`} sub="cohort retained on paid" />
            </StatGrid>
            <StatGrid cols={4}>
              <StatCard icon={<TrendingUp />} label="Conversion Rate" value={`${m.conversion_rate_pct ?? 0}%`} sub={`${m.conversions ?? 0} free→paid in ${days}d`} highlight />
              {Object.entries(m.plan_counts || {}).map(([code, count]) => (
                <StatCard key={code} icon={<Users />} label={code.replace(/_/g, " ")} value={count?.toLocaleString()} />
              ))}
            </StatGrid>
          </>
        )}

        {/* Forecast chart */}
        {!fLoad && chartData.length > 0 && (
          <Card padding="md">
            <div className="flex items-center justify-between mb-3">
              <div className="text-sm font-semibold text-slate-800">Revenue History & Forecast</div>
              <div className="text-xs text-slate-500">
                {fc.growth_rate_pct > 0 ? "+" : ""}{fc.growth_rate_pct}% growth trend · {fc.methodology}
              </div>
            </div>
            <ResponsiveContainer width="100%" height={200}>
              <LineChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                <XAxis dataKey="month" tick={{ fontSize: 10, fill: "#64748b" }} />
                <YAxis tick={{ fontSize: 10, fill: "#64748b" }} tickFormatter={(v) => `€${v}`} />
                <Tooltip {...CHART_OPTS} formatter={(v) => v ? `€${v}` : "—"} />
                <Legend wrapperStyle={{ fontSize: 11 }} />
                <Line type="monotone" dataKey="revenue_eur"   name="Actual"    stroke="#0F2847" strokeWidth={2} dot={{ r: 3 }} connectNulls={false} />
                <Line type="monotone" dataKey="projected_eur" name="Forecast"  stroke="#059669" strokeWidth={2} strokeDasharray="6 3" dot={{ r: 3 }} connectNulls={false} />
              </LineChart>
            </ResponsiveContainer>
          </Card>
        )}

        {/* By Country */}
        {!cLoad && (byCountry?.items || []).length > 0 && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <Card padding="md">
              <div className="text-sm font-semibold text-slate-800 mb-3">Revenue by Country</div>
              <ResponsiveContainer width="100%" height={220}>
                <BarChart data={byCountry.items.slice(0, 10)} layout="vertical">
                  <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" horizontal={false} />
                  <XAxis type="number" tick={{ fontSize: 10, fill: "#64748b" }} tickFormatter={(v) => `€${v}`} />
                  <YAxis type="category" dataKey="country" tick={{ fontSize: 10, fill: "#64748b" }} width={80} />
                  <Tooltip {...CHART_OPTS} formatter={(v) => `€${v}`} />
                  <Bar dataKey="mrr_eur" name="MRR (EUR)" fill="#0F2847" radius={[0, 3, 3, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </Card>

            <Card padding="md">
              <div className="text-sm font-semibold text-slate-800 mb-3">Users by Country (top 10)</div>
              <div className="space-y-3 overflow-y-auto max-h-56">
                {byCountry.items.slice(0, 10).map((c) => (
                  <div key={c.country} className="flex items-center gap-3">
                    <span className="text-xs text-slate-500 w-24 truncate">{c.country || "Unknown"}</span>
                    <ProgressBar
                      value={c.users}
                      max={Math.max(...byCountry.items.map((x) => x.users), 1)}
                      showValue={false}
                      size="sm"
                      className="flex-1"
                    />
                    <span className="text-xs text-slate-900 w-8 text-right">{c.users}</span>
                    <span className="text-xs text-slate-500 w-16 text-right">€{c.mrr_eur}</span>
                  </div>
                ))}
              </div>
            </Card>
          </div>
        )}
      </div>
    </AdministrationLayout>
  );
}
