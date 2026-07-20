import React, { useState, useCallback, useEffect } from "react";
import {
  AreaChart, Area, BarChart, Bar, LineChart, Line,
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend,
} from "recharts";
import { DollarSign, TrendingUp, TrendingDown, Users, RefreshCw } from "lucide-react";
import api from "@/lib/api";
import { NAVY } from "@/lib/tokens";
import { AdministrationLayout } from "@/layouts";

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

function KpiCard({ icon: Icon, label, value, sub, highlight }) {
  return (
    <div className={`bg-[#0F2847] border p-4 ${highlight ? "border-green-700/60" : "border-[#1a3050]"}`}>
      <div className="flex items-start justify-between">
        <div>
          <div className="text-xs text-slate-400 mb-1">{label}</div>
          <div className={`text-2xl font-bold ${highlight ? "text-green-400" : "text-white"}`}>{value ?? "—"}</div>
          {sub && <div className="text-[10px] text-slate-500 mt-1">{sub}</div>}
        </div>
        <Icon size={16} className="text-slate-500 flex-shrink-0 mt-1" />
      </div>
    </div>
  );
}

const CHART_OPTS = { contentStyle: { backgroundColor: "#0B1C35", border: "1px solid #1a3050", fontSize: 12 } };

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
          <select
            value={days}
            onChange={(e) => setDays(Number(e.target.value))}
            className="text-xs bg-[#0F2847] border border-[#1a3050] text-slate-300 px-2 py-1.5"
          >
            <option value={30}>30 days</option>
            <option value={60}>60 days</option>
            <option value={90}>90 days</option>
          </select>
          <button onClick={() => { refMetrics(); refCountry(); refForecast(); }}
            className="p-1.5 bg-[#0F2847] border border-[#1a3050] text-slate-400 hover:text-white">
            <RefreshCw size={14} className={loading ? "animate-spin" : ""} />
          </button>
        </div>
      }
    >

      {/* Primary KPIs */}
      {!mLoad && (
        <>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            <KpiCard icon={DollarSign}  label="MRR (EUR)"         value={`€${m.mrr_eur?.toLocaleString()}`}    highlight />
            <KpiCard icon={TrendingUp}  label="ARR (EUR)"         value={`€${m.arr_eur?.toLocaleString()}`}    highlight />
            <KpiCard icon={DollarSign}  label="ARPU (EUR)"        value={`€${m.arpu_eur}`}                     sub="per active subscriber" />
            <KpiCard icon={TrendingUp}  label="LTV (EUR)"         value={m.ltv_eur ? `€${m.ltv_eur}` : "N/A"} sub="ARPU ÷ churn rate" />
          </div>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            <KpiCard icon={DollarSign}  label="CAC (EUR)"         value={m.cac_eur ? `€${m.cac_eur}` : "N/A"} sub="estimated cost per acquisition" />
            <KpiCard icon={Users}       label="Active Subscribers" value={m.active_subscribers?.toLocaleString()} sub={`of ${m.total_users?.toLocaleString()} total users`} />
            <KpiCard icon={TrendingDown} label="Churn Rate"        value={`${m.churn_rate_pct ?? 0}%`}          sub={`${m.churned_period ?? 0} churned in ${days}d`} color="red" />
            <KpiCard icon={TrendingUp}  label="Retention Rate"     value={`${m.retention_rate_pct ?? 0}%`}      sub="cohort retained on paid" />
          </div>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            <KpiCard icon={TrendingUp}  label="Conversion Rate"   value={`${m.conversion_rate_pct ?? 0}%`}      sub={`${m.conversions ?? 0} free→paid in ${days}d`} highlight />
            {Object.entries(m.plan_counts || {}).map(([code, count]) => (
              <KpiCard key={code} icon={Users} label={code.replace(/_/g, " ")} value={count?.toLocaleString()} />
            ))}
          </div>
        </>
      )}

      {/* Forecast chart */}
      {!fLoad && chartData.length > 0 && (
        <div className="bg-[#0F2847] border border-[#1a3050] p-4">
          <div className="flex items-center justify-between mb-3">
            <div className="text-sm font-semibold text-white">Revenue History & Forecast</div>
            <div className="text-xs text-slate-400">
              {fc.growth_rate_pct > 0 ? "+" : ""}{fc.growth_rate_pct}% growth trend · {fc.methodology}
            </div>
          </div>
          <ResponsiveContainer width="100%" height={200}>
            <LineChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1a3050" />
              <XAxis dataKey="month" tick={{ fontSize: 10, fill: "#94a3b8" }} />
              <YAxis tick={{ fontSize: 10, fill: "#94a3b8" }} tickFormatter={(v) => `€${v}`} />
              <Tooltip {...CHART_OPTS} formatter={(v) => v ? `€${v}` : "—"} />
              <Legend wrapperStyle={{ fontSize: 11 }} />
              <Line type="monotone" dataKey="revenue_eur"   name="Actual"    stroke="#3b82f6" strokeWidth={2} dot={{ r: 3 }} connectNulls={false} />
              <Line type="monotone" dataKey="projected_eur" name="Forecast"  stroke="#22c55e" strokeWidth={2} strokeDasharray="6 3" dot={{ r: 3 }} connectNulls={false} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* By Country */}
      {!cLoad && (byCountry?.items || []).length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="bg-[#0F2847] border border-[#1a3050] p-4">
            <div className="text-sm font-semibold text-white mb-3">Revenue by Country</div>
            <ResponsiveContainer width="100%" height={220}>
              <BarChart data={byCountry.items.slice(0, 10)} layout="vertical">
                <CartesianGrid strokeDasharray="3 3" stroke="#1a3050" horizontal={false} />
                <XAxis type="number" tick={{ fontSize: 10, fill: "#94a3b8" }} tickFormatter={(v) => `€${v}`} />
                <YAxis type="category" dataKey="country" tick={{ fontSize: 10, fill: "#94a3b8" }} width={80} />
                <Tooltip {...CHART_OPTS} formatter={(v) => `€${v}`} />
                <Bar dataKey="mrr_eur" name="MRR (EUR)" fill="#3b82f6" radius={[0, 3, 3, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>

          <div className="bg-[#0F2847] border border-[#1a3050] p-4">
            <div className="text-sm font-semibold text-white mb-3">Users by Country (top 10)</div>
            <div className="space-y-2 overflow-y-auto max-h-56">
              {byCountry.items.slice(0, 10).map((c) => (
                <div key={c.country} className="flex items-center gap-3">
                  <span className="text-xs text-slate-400 w-24 truncate">{c.country || "Unknown"}</span>
                  <div className="flex-1 h-1.5 bg-[#1a3050] rounded-full overflow-hidden">
                    <div
                      className="h-full bg-blue-500"
                      style={{
                        width: `${Math.min(100, (c.users / Math.max(...byCountry.items.map((x) => x.users), 1)) * 100)}%`
                      }}
                    />
                  </div>
                  <span className="text-xs text-white w-8 text-right">{c.users}</span>
                  <span className="text-xs text-slate-500 w-16 text-right">€{c.mrr_eur}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </AdministrationLayout>
  );
}
