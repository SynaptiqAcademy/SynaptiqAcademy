/* eslint-disable */
import React, { useState, useCallback, useEffect } from "react";
import { RefreshCw, AlertTriangle, TrendingUp, Zap } from "lucide-react";
import { AreaChart, Area, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from "recharts";
import api from "@/lib/api";
import { NAVY } from "@/lib/tokens";
import { AdministrationLayout } from "@/layouts";

function useX(path, params = {}) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const query = new URLSearchParams(params).toString();
  const load = useCallback(() => {
    setLoading(true);
    api.get(`/admin/x/${path}${query ? "?" + query : ""}`)
      .then(r => setData(r.data)).catch(() => setData(null)).finally(() => setLoading(false));
  }, [path, query]);
  useEffect(() => { load(); }, [load]);
  return { data, loading, refetch: load };
}

const ALERT_SEVERITY = {
  high:   "border-l-red-500 bg-red-900/20 text-red-300",
  medium: "border-l-yellow-500 bg-yellow-900/20 text-yellow-300",
  low:    "border-l-blue-500 bg-blue-900/20 text-blue-300",
};

export default function AdminApiMonitor() {
  const [days, setDays] = useState(7);
  const { data: ov,    loading: ovL,    refetch: refOv    } = useX("api-monitor/overview", { days });
  const { data: alerts, loading: alL,   refetch: refAlerts } = useX("api-monitor/alerts");
  const refetchAll = () => { refOv(); refAlerts(); };

  const d = ov || {};
  const al = alerts?.alerts || [];

  const healthColor = d.health_score >= 90 ? "text-green-400" : d.health_score >= 70 ? "text-yellow-400" : "text-red-400";

  return (
    <AdministrationLayout
      title="API Monitoring & Observability Center"
      subtitle="Per-endpoint stats, latency, error rates, and health scoring"
      actions={
        <div className="flex gap-2">
          <select value={days} onChange={e => setDays(Number(e.target.value))}
            className="text-xs bg-[#0F2847] border border-[#1a3050] text-slate-300 px-2 py-1.5">
            {[1, 7, 14, 30, 90].map(d => <option key={d} value={d}>Last {d}d</option>)}
          </select>
          <button onClick={refetchAll} className="p-1.5 bg-[#0F2847] border border-[#1a3050] text-slate-400 hover:text-white">
            <RefreshCw size={14} className={(ovL || alL) ? "animate-spin" : ""} />
          </button>
        </div>
      }
    >

      {/* KPI row */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
        <div className="bg-[#0F2847] border border-[#1a3050] p-4">
          <div className={`text-3xl font-bold ${healthColor}`}>{d.health_score ?? "—"}</div>
          <div className="text-xs text-slate-400">Health Score</div>
        </div>
        <div className="bg-[#0F2847] border border-[#1a3050] p-4">
          <div className="text-xl font-bold text-white">{(d.total_requests || 0).toLocaleString()}</div>
          <div className="text-xs text-slate-400">Total Requests</div>
        </div>
        <div className="bg-[#0F2847] border border-[#1a3050] p-4">
          <div className="text-xl font-bold text-green-400">{d.success_rate_pct ?? 0}%</div>
          <div className="text-xs text-slate-400">Success Rate</div>
        </div>
        <div className="bg-[#0F2847] border border-[#1a3050] p-4">
          <div className={`text-xl font-bold ${d.error_rate_pct > 5 ? "text-red-400" : "text-yellow-400"}`}>{d.error_rate_pct ?? 0}%</div>
          <div className="text-xs text-slate-400">Error Rate</div>
        </div>
        <div className="bg-[#0F2847] border border-[#1a3050] p-4">
          <div className={`text-xl font-bold ${d.avg_response_ms > 500 ? "text-red-400" : d.avg_response_ms > 200 ? "text-yellow-400" : "text-green-400"}`}>{d.avg_response_ms ?? 0}ms</div>
          <div className="text-xs text-slate-400">Avg Latency</div>
        </div>
        <div className="bg-[#0F2847] border border-[#1a3050] p-4">
          <div className={`text-xl font-bold ${al.length > 0 ? "text-red-400" : "text-green-400"}`}>{al.length}</div>
          <div className="text-xs text-slate-400">Active Alerts</div>
        </div>
      </div>

      {/* Alerts */}
      {al.length > 0 && (
        <div className="space-y-2">
          <div className="text-xs font-semibold uppercase tracking-widest text-slate-500">Active Alerts</div>
          {al.map((a, i) => (
            <div key={i} className={`border-l-2 p-3 text-xs ${ALERT_SEVERITY[a.severity] || ALERT_SEVERITY.low}`}>
              <span className="font-medium uppercase text-[10px] mr-2">{a.type}</span>
              {a.message}
            </div>
          ))}
        </div>
      )}

      {/* Traffic trend */}
      {(d.daily_trend || []).length > 0 && (
        <div className="bg-[#0F2847] border border-[#1a3050] p-4">
          <div className="text-xs text-slate-500 font-medium mb-3">Daily Traffic Trend</div>
          <ResponsiveContainer width="100%" height={180}>
            <AreaChart data={d.daily_trend}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1a3050" />
              <XAxis dataKey="date" tick={{ fill: "#64748b", fontSize: 10 }} tickFormatter={v => v.slice(5)} />
              <YAxis tick={{ fill: "#64748b", fontSize: 10 }} />
              <Tooltip contentStyle={{ background: "#0B1C35", border: "1px solid #1a3050", fontSize: 11 }} />
              <Legend wrapperStyle={{ fontSize: 11, color: "#94a3b8" }} />
              <Area type="monotone" dataKey="requests" stroke="#3b82f6" fill="#3b82f6" fillOpacity={0.15} strokeWidth={1.5} name="Requests" />
              <Area type="monotone" dataKey="errors" stroke="#ef4444" fill="#ef4444" fillOpacity={0.15} strokeWidth={1.5} name="Errors" />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Top endpoints */}
        <div className="bg-[#0F2847] border border-[#1a3050]">
          <div className="flex items-center gap-2 px-4 py-3 border-b border-[#1a3050]">
            <TrendingUp size={14} className="text-blue-400" />
            <span className="text-sm font-semibold text-white">Top Endpoints by Volume</span>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-xs text-slate-300">
              <thead className="text-slate-500 border-b border-[#1a3050]">
                <tr>
                  <th className="text-left px-3 py-2 font-medium">Endpoint</th>
                  <th className="text-right px-3 py-2 font-medium">Requests</th>
                  <th className="text-right px-3 py-2 font-medium">Errors</th>
                  <th className="text-right px-3 py-2 font-medium">Avg ms</th>
                </tr>
              </thead>
              <tbody>
                {(d.top_endpoints || []).slice(0, 12).map((ep, i) => (
                  <tr key={i} className="border-t border-[#1a3050] hover:bg-[#1a3050]/30">
                    <td className="px-3 py-1.5 font-mono text-[10px] text-slate-300 max-w-[200px] truncate">
                      <span className="text-slate-500 mr-1">{ep.method}</span>{ep.endpoint}
                    </td>
                    <td className="px-3 py-1.5 text-right text-white">{ep.requests}</td>
                    <td className="px-3 py-1.5 text-right">
                      <span className={ep.error_rate > 5 ? "text-red-400" : "text-slate-400"}>{ep.errors}</span>
                    </td>
                    <td className="px-3 py-1.5 text-right text-slate-400">{ep.avg_ms}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Slowest endpoints */}
        <div className="bg-[#0F2847] border border-[#1a3050]">
          <div className="flex items-center gap-2 px-4 py-3 border-b border-[#1a3050]">
            <Zap size={14} className="text-yellow-400" />
            <span className="text-sm font-semibold text-white">Slowest Endpoints</span>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-xs text-slate-300">
              <thead className="text-slate-500 border-b border-[#1a3050]">
                <tr>
                  <th className="text-left px-3 py-2 font-medium">Endpoint</th>
                  <th className="text-right px-3 py-2 font-medium">Avg ms</th>
                  <th className="text-right px-3 py-2 font-medium">Max ms</th>
                </tr>
              </thead>
              <tbody>
                {(d.slowest_endpoints || []).map((ep, i) => (
                  <tr key={i} className="border-t border-[#1a3050] hover:bg-[#1a3050]/30">
                    <td className="px-3 py-1.5 font-mono text-[10px] text-slate-300 max-w-[220px] truncate">
                      <span className="text-slate-500 mr-1">{ep.method}</span>{ep.endpoint}
                    </td>
                    <td className="px-3 py-1.5 text-right">
                      <span className={ep.avg_ms > 500 ? "text-red-400" : ep.avg_ms > 200 ? "text-yellow-400" : "text-green-400"}>{ep.avg_ms}</span>
                    </td>
                    <td className="px-3 py-1.5 text-right text-slate-400">{ep.max_ms}</td>
                  </tr>
                ))}
                {(d.slowest_endpoints || []).length === 0 && (
                  <tr><td colSpan={3} className="px-3 py-6 text-center text-slate-500">No data yet — collect more traffic first</td></tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </AdministrationLayout>
  );
}
