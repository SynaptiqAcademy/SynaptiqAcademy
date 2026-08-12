import React, { useState, useCallback, useEffect } from "react";
import { RefreshCw, Search, BarChart3, TrendingUp } from "lucide-react";
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell } from "recharts";
import api from "@/lib/api";
import { NAVY, EMERALD, AMBER, CRIMSON } from "@/lib/tokens";
import { AdministrationLayout } from "@/layouts";
import { Card, Button, FormSelect, StatCard, StatGrid, Tag, TagGroup } from "@/components/ds";

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

  const qualColor = o.search_quality_score >= 75 ? EMERALD : o.search_quality_score >= 50 ? AMBER : CRIMSON;

  return (
    <AdministrationLayout
      title="Search & Discovery Observatory"
      subtitle="Keyword analytics, empty result detection, module usage"
      actions={
        <div className="flex gap-2">
          <FormSelect value={days} onChange={e => setDays(Number(e.target.value))} wrapperClassName="!mb-0" size="sm">
            {[7, 14, 30, 90].map(d => <option key={d} value={d}>Last {d}d</option>)}
          </FormSelect>
          <Button variant="ghost" size="icon" onClick={refetchAll} aria-label="Refresh">
            <RefreshCw size={14} className={(ovL || kwL) ? "animate-spin" : ""} />
          </Button>
        </div>
      }
    >
      <div className="flex flex-col gap-6">
        {/* KPI row */}
        <StatGrid cols={6}>
          <StatCard label="Search Quality" value={`${o.search_quality_score ?? 0}`} />
          <StatCard label="Total Searches" value={(o.total_searches || 0).toLocaleString()} />
          <StatCard label="Unique Users" value={o.unique_users ?? 0} />
          <StatCard label="Unique Queries" value={o.unique_queries ?? 0} />
          <StatCard label="Empty Results" value={o.empty_results ?? 0} />
          <StatCard label="Empty Rate" value={`${o.empty_rate_pct ?? 0}%`} />
        </StatGrid>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          {/* By module */}
          {byModule.length > 0 && (
            <Card padding="md">
              <div className="flex items-center gap-2 mb-3">
                <BarChart3 size={14} className="text-blue-500" />
                <span className="text-sm font-semibold text-slate-800">Searches by Module</span>
              </div>
              <ResponsiveContainer width="100%" height={200}>
                <BarChart data={byModule} layout="vertical" margin={{ left: 20, right: 10 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" horizontal={false} />
                  <XAxis type="number" tick={{ fill: "#64748b", fontSize: 10 }} />
                  <YAxis type="category" dataKey="module" tick={{ fill: "#64748b", fontSize: 10 }} width={110} />
                  <Tooltip contentStyle={{ background: "#ffffff", border: "1px solid #e2e8f0", fontSize: 11 }} />
                  <Bar dataKey="count" fill="#0F2847" radius={[0, 2, 2, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </Card>
          )}

          {/* Empty results modules */}
          <Card padding="md">
            <div className="flex items-center gap-2 mb-3">
              <Search size={14} className="text-amber-500" />
              <span className="text-sm font-semibold text-slate-800">Module Performance</span>
            </div>
            <div className="space-y-2 overflow-y-auto max-h-[220px]">
              {byModule.map(m => (
                <div key={m.module} className="flex items-center justify-between text-xs">
                  <span className="text-slate-600 truncate flex-1">{m.module}</span>
                  <span className="text-slate-900 mx-3">{m.count}</span>
                  <div className="text-right">
                    <span className="text-slate-400">avg {m.avg_results} results</span>
                  </div>
                </div>
              ))}
              {byModule.length === 0 && <div className="text-xs text-slate-400">No search data yet for this period</div>}
            </div>
          </Card>
        </div>

        {/* Top keywords */}
        <Card padding="none">
          <div className="flex items-center justify-between px-4 py-3 border-b border-slate-200">
            <div className="flex items-center gap-2">
              <TrendingUp size={14} className="text-emerald-500" />
              <span className="text-sm font-semibold text-slate-800">Top Search Keywords</span>
            </div>
            <FormSelect value={kwLimit} onChange={e => setKwLimit(Number(e.target.value))} wrapperClassName="!mb-0" size="sm">
              <option value={20}>Top 20</option>
              <option value={30}>Top 30</option>
              <option value={50}>Top 50</option>
            </FormSelect>
          </div>
          <div className="p-4">
            {keywords.length === 0 ? (
              <div className="text-xs text-slate-400 text-center py-4">No search queries logged yet</div>
            ) : (
              <TagGroup gap={8}>
                {keywords.map((kw, i) => {
                  const maxCount = keywords[0]?.count || 1;
                  const size = Math.max(10, Math.min(16, 10 + (kw.count / maxCount) * 6));
                  return (
                    <Tag key={i} color={kw.avg_results === 0 ? CRIMSON : undefined} style={{ fontSize: size }}>
                      {kw.query}
                      <span className="text-[10px] opacity-70 ml-1">({kw.count})</span>
                    </Tag>
                  );
                })}
              </TagGroup>
            )}
            {keywords.some(k => k.avg_results === 0) && (
              <div className="mt-3 text-[10px] text-red-600">Red keywords returned 0 results — improve search coverage for these terms</div>
            )}
          </div>
        </Card>
      </div>
    </AdministrationLayout>
  );
}
