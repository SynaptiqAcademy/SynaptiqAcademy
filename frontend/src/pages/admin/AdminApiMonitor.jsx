/* eslint-disable */
import React, { useState, useCallback, useEffect } from "react";
import { RefreshCw, TrendingUp, Zap } from "lucide-react";
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from "recharts";
import api from "@/lib/api";
import { EMERALD, AMBER, CRIMSON, INFO, BRD_SOFT, TEXT_MUTED, WHITE, BRD } from "@/lib/tokens";
import { AdministrationLayout } from "@/layouts";
import { Button, Card, StatCard, StatGrid, DataTable, FormSelect } from "@/components/ds";

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

const ALERT_ACCENT = { high: CRIMSON, medium: AMBER, low: INFO };

export default function AdminApiMonitor() {
  const [days, setDays] = useState(7);
  const { data: ov,    loading: ovL,    refetch: refOv    } = useX("api-monitor/overview", { days });
  const { data: alerts, loading: alL,   refetch: refAlerts } = useX("api-monitor/alerts");
  const refetchAll = () => { refOv(); refAlerts(); };

  const d = ov || {};
  const al = alerts?.alerts || [];

  const healthColor = d.health_score >= 90 ? EMERALD : d.health_score >= 70 ? AMBER : CRIMSON;

  const topEndpointColumns = [
    {
      key: "endpoint", label: "Endpoint", maxWidth: 220, wrap: false,
      render: (v, row) => (
        <span className="font-mono text-[11px]">
          <span className="text-slate-400 mr-1">{row.method}</span>{v}
        </span>
      ),
    },
    { key: "requests", label: "Requests", align: "right" },
    {
      key: "errors", label: "Errors", align: "right",
      render: (v, row) => <span style={{ color: row.error_rate > 5 ? CRIMSON : undefined }}>{v}</span>,
    },
    { key: "avg_ms", label: "Avg ms", align: "right" },
  ];

  const slowestColumns = [
    {
      key: "endpoint", label: "Endpoint", maxWidth: 220, wrap: false,
      render: (v, row) => (
        <span className="font-mono text-[11px]">
          <span className="text-slate-400 mr-1">{row.method}</span>{v}
        </span>
      ),
    },
    {
      key: "avg_ms", label: "Avg ms", align: "right",
      render: (v) => <span style={{ color: v > 500 ? CRIMSON : v > 200 ? AMBER : EMERALD }}>{v}</span>,
    },
    { key: "max_ms", label: "Max ms", align: "right" },
  ];

  return (
    <AdministrationLayout
      title="API Monitoring & Observability Center"
      subtitle="Per-endpoint stats, latency, error rates, and health scoring"
      actions={
        <div className="flex gap-2 items-center">
          <FormSelect value={days} onChange={e => setDays(Number(e.target.value))} size="sm" wrapperClassName="w-28">
            {[1, 7, 14, 30, 90].map(d => <option key={d} value={d}>Last {d}d</option>)}
          </FormSelect>
          <Button variant="ghost" size="icon" onClick={refetchAll} aria-label="Refresh">
            <RefreshCw size={14} className={(ovL || alL) ? "animate-spin" : ""} />
          </Button>
        </div>
      }
    >

      {/* KPI row */}
      <StatGrid cols={6}>
        <StatCard label="Health Score" value={d.health_score ?? "—"} />
        <StatCard label="Total Requests" value={(d.total_requests || 0).toLocaleString()} />
        <StatCard label="Success Rate" value={`${d.success_rate_pct ?? 0}%`} />
        <StatCard label="Error Rate" value={`${d.error_rate_pct ?? 0}%`} />
        <StatCard label="Avg Latency" value={`${d.avg_response_ms ?? 0}ms`} />
        <StatCard label="Active Alerts" value={al.length} />
      </StatGrid>

      {/* Alerts */}
      {al.length > 0 && (
        <div className="space-y-2">
          <div className="text-xs font-semibold uppercase tracking-widest text-slate-500">Active Alerts</div>
          {al.map((a, i) => (
            <Card key={i} padding="sm" accent={ALERT_ACCENT[a.severity] || ALERT_ACCENT.low} className="text-xs">
              <span className="font-medium uppercase text-[10px] mr-2 text-slate-500">{a.type}</span>
              <span className="text-slate-700">{a.message}</span>
            </Card>
          ))}
        </div>
      )}

      {/* Traffic trend — kept as recharts (multi-series area chart with tooltip
          and legend); ds/Chart's LineChart has no tooltip/legend support, so
          this custom chart-drawing logic stays, only its chrome (surrounding
          card, colors, axis ticks) is restyled for the light theme. */}
      {(d.daily_trend || []).length > 0 && (
        <Card padding="lg">
          <div className="text-xs text-slate-500 font-medium mb-3">Daily Traffic Trend</div>
          <ResponsiveContainer width="100%" height={180}>
            <AreaChart data={d.daily_trend}>
              <CartesianGrid strokeDasharray="3 3" stroke={BRD_SOFT} />
              <XAxis dataKey="date" tick={{ fill: TEXT_MUTED, fontSize: 10 }} tickFormatter={v => v.slice(5)} />
              <YAxis tick={{ fill: TEXT_MUTED, fontSize: 10 }} />
              <Tooltip contentStyle={{ background: WHITE, border: `1px solid ${BRD}`, fontSize: 11 }} />
              <Legend wrapperStyle={{ fontSize: 11, color: TEXT_MUTED }} />
              <Area type="monotone" dataKey="requests" stroke={INFO} fill={INFO} fillOpacity={0.12} strokeWidth={1.5} name="Requests" />
              <Area type="monotone" dataKey="errors" stroke={CRIMSON} fill={CRIMSON} fillOpacity={0.12} strokeWidth={1.5} name="Errors" />
            </AreaChart>
          </ResponsiveContainer>
        </Card>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Top endpoints */}
        <Card padding="none">
          <div className="flex items-center gap-2 px-4 py-3 border-b border-slate-100">
            <TrendingUp size={14} style={{ color: INFO }} />
            <span className="text-sm font-semibold text-slate-800">Top Endpoints by Volume</span>
          </div>
          <DataTable columns={topEndpointColumns} rows={(d.top_endpoints || []).slice(0, 12)} />
        </Card>

        {/* Slowest endpoints */}
        <Card padding="none">
          <div className="flex items-center gap-2 px-4 py-3 border-b border-slate-100">
            <Zap size={14} style={{ color: AMBER }} />
            <span className="text-sm font-semibold text-slate-800">Slowest Endpoints</span>
          </div>
          <DataTable
            columns={slowestColumns}
            rows={d.slowest_endpoints || []}
            emptyNode={
              <div className="px-3 py-6 text-center text-slate-400 text-xs">
                No data yet — collect more traffic first
              </div>
            }
          />
        </Card>
      </div>
    </AdministrationLayout>
  );
}
