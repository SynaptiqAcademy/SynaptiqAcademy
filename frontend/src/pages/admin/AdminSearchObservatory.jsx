import React, { useState, useCallback, useEffect } from "react";
import { RefreshCw, Search, BarChart3, TrendingUp } from "lucide-react";
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell } from "recharts";
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

export default function AdminSearchObservatory() {
  const [days, setDays]       = useState(30);
  const [kwLimit, setKwLimit] = useState(30);

  const { data: ov, loading: ovL, refetch: refOv } = useX("search/overview", { days });
  const { data: kw, loading: kwL, refetch: refKw } = useX("search/keywords", { days, limit: kwLimit });
  const refetchAll = () => { refOv(); refKw(); };

  const o  = ov || {};
  const keywords = (kw?.items || []).slice(0, 30);
  const byModule = (o.by_module || []).slice(0, 10);

  const qualColor = o.search_quality_score >= 75 ? "text-green-400" : o.search_quality_score >= 50 ? "text-yellow-400" : "text-red-400";

  return (
    <AdministrationLayout
      title="Search & Discovery Observatory"
      subtitle="Keyword analytics, empty result detection, module usage"
      actions={
        <div className="flex gap-2">
          <select value={days} onChange={e => setDays(Number(e.target.value))}
            className="text-xs bg-[#0F2847] border border-[#1a3050] text-slate-300 px-2 py-1.5">
            {[7, 14, 30, 90].map(d => <option key={d} value={d}>Last {d}d</option>)}
          </select>
          <button onClick={refetchAll} className="p-1.5 bg-[#0F2847] border border-[#1a3050] text-slate-400 hover:text-white">
            <RefreshCw size={14} className={(ovL || kwL) ? "animate-spin" : ""} />
          </button>
        </div>
      }
    >

      {/* KPI row */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
        {[
          { label: "Search Quality", value: `${o.search_quality_score ?? 0}`, color: qualColor },
          { label: "Total Searches", value: (o.total_searches || 0).toLocaleString(), color: "text-white" },
          { label: "Unique Users", value: o.unique_users ?? 0, color: "text-blue-400" },
          { label: "Unique Queries", value: o.unique_queries ?? 0, color: "text-purple-400" },
          { label: "Empty Results", value: o.empty_results ?? 0, color: "text-red-400" },
          { label: "Empty Rate", value: `${o.empty_rate_pct ?? 0}%`, color: o.empty_rate_pct > 20 ? "text-red-400" : "text-yellow-400" },
        ].map(({ label, value, color }) => (
          <div key={label} className="bg-[#0F2847] border border-[#1a3050] p-4">
            <div className={`text-xl font-bold ${color}`}>{value}</div>
            <div className="text-xs text-slate-400">{label}</div>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* By module */}
        {byModule.length > 0 && (
          <div className="bg-[#0F2847] border border-[#1a3050] p-4">
            <div className="flex items-center gap-2 mb-3">
              <BarChart3 size={14} className="text-blue-400" />
              <span className="text-sm font-semibold text-white">Searches by Module</span>
            </div>
            <ResponsiveContainer width="100%" height={200}>
              <BarChart data={byModule} layout="vertical" margin={{ left: 20, right: 10 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1a3050" horizontal={false} />
                <XAxis type="number" tick={{ fill: "#64748b", fontSize: 10 }} />
                <YAxis type="category" dataKey="module" tick={{ fill: "#94a3b8", fontSize: 10 }} width={110} />
                <Tooltip contentStyle={{ background: "#0B1C35", border: "1px solid #1a3050", fontSize: 11 }} />
                <Bar dataKey="count" fill="#3b82f6" radius={[0, 2, 2, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        )}

        {/* Empty results modules */}
        <div className="bg-[#0F2847] border border-[#1a3050] p-4">
          <div className="flex items-center gap-2 mb-3">
            <Search size={14} className="text-yellow-400" />
            <span className="text-sm font-semibold text-white">Module Performance</span>
          </div>
          <div className="space-y-2 overflow-y-auto max-h-[220px]">
            {byModule.map(m => (
              <div key={m.module} className="flex items-center justify-between text-xs">
                <span className="text-slate-300 truncate flex-1">{m.module}</span>
                <span className="text-white mx-3">{m.count}</span>
                <div className="text-right">
                  <span className="text-slate-500">avg {m.avg_results} results</span>
                </div>
              </div>
            ))}
            {byModule.length === 0 && <div className="text-xs text-slate-500">No search data yet for this period</div>}
          </div>
        </div>
      </div>

      {/* Top keywords */}
      <div className="bg-[#0F2847] border border-[#1a3050]">
        <div className="flex items-center justify-between px-4 py-3 border-b border-[#1a3050]">
          <div className="flex items-center gap-2">
            <TrendingUp size={14} className="text-green-400" />
            <span className="text-sm font-semibold text-white">Top Search Keywords</span>
          </div>
          <select value={kwLimit} onChange={e => setKwLimit(Number(e.target.value))}
            className="text-[10px] bg-[#0B1C35] border border-[#1a3050] text-slate-400 px-1.5 py-1">
            <option value={20}>Top 20</option>
            <option value={30}>Top 30</option>
            <option value={50}>Top 50</option>
          </select>
        </div>
        <div className="p-4">
          {keywords.length === 0 ? (
            <div className="text-xs text-slate-500 text-center py-4">No search queries logged yet</div>
          ) : (
            <div className="flex flex-wrap gap-2">
              {keywords.map((kw, i) => {
                const maxCount = keywords[0]?.count || 1;
                const size = Math.max(10, Math.min(16, 10 + (kw.count / maxCount) * 6));
                return (
                  <span key={i} className={`px-2 py-1 bg-[#0B1C35] border border-[#1a3050] text-slate-300
                    ${kw.avg_results === 0 ? "border-red-700/50 text-red-400" : ""}`}
                    style={{ fontSize: size }}>
                    {kw.query}
                    <span className="text-slate-500 text-[10px] ml-1">({kw.count})</span>
                  </span>
                );
              })}
            </div>
          )}
          {keywords.some(k => k.avg_results === 0) && (
            <div className="mt-3 text-[10px] text-red-400">Red keywords returned 0 results — improve search coverage for these terms</div>
          )}
        </div>
      </div>
    </AdministrationLayout>
  );
}
