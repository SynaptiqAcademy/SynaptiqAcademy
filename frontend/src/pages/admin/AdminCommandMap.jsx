/* eslint-disable */
import React, { useState, useCallback, useEffect } from "react";
import { RefreshCw, CheckCircle, AlertTriangle, XCircle, ExternalLink } from "lucide-react";
import api from "@/lib/api";
import { EMERALD, AMBER, CRIMSON, TEXT_MUTED } from "@/lib/tokens";
import { AdministrationLayout } from "@/layouts";
import { Spinner, Button, Card, StatCard, StatGrid, MiniBar } from "@/components/ds";

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

const STATUS_META = {
  healthy:  { Icon: CheckCircle,  color: EMERALD, variant: "success" },
  degraded: { Icon: AlertTriangle, color: AMBER,   variant: "warning" },
  error:    { Icon: XCircle,      color: CRIMSON, variant: "danger" },
};

function ModuleCard({ module }) {
  const { Icon, color, variant } = STATUS_META[module.status] || STATUS_META.healthy;

  return (
    <Card to={module.route} padding="sm" accent={color} className="group">
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <Icon size={14} style={{ color }} />
          <span className="text-xs font-medium text-slate-800">{module.name}</span>
        </div>
        <ExternalLink size={10} className="text-slate-300 group-hover:text-slate-500 transition-colors" />
      </div>
      <div className="flex items-center gap-3 text-[10px] text-slate-500">
        <span>{(module.records || 0).toLocaleString()} records</span>
        {module.errors_24h > 0 && (
          <span style={{ color: CRIMSON }}>{module.errors_24h} errors/24h</span>
        )}
        {!module.env_ok && (
          <span style={{ color: AMBER }}>env missing</span>
        )}
      </div>
    </Card>
  );
}

export default function AdminCommandMap() {
  const { data, loading, refetch } = useX("command-map");

  const d = data || {};
  const modules = d.modules || [];
  const healthy  = modules.filter(m => m.status === "healthy");
  const degraded = modules.filter(m => m.status === "degraded");
  const errored  = modules.filter(m => m.status === "error");

  const scoreColor = d.overall_score >= 90 ? EMERALD : d.overall_score >= 70 ? AMBER : CRIMSON;

  return (
    <AdministrationLayout
      title="Platform Command Map"
      subtitle={`Real-time health status of all ${d.module_count || 20} platform modules`}
      actions={
        <Button variant="ghost" size="icon" onClick={refetch} aria-label="Refresh">
          <RefreshCw size={14} className={loading ? "animate-spin" : ""} />
        </Button>
      }
    >

      {/* Header stats */}
      <StatGrid cols={5}>
        <StatCard label="Platform Score" value={d.overall_score ?? "—"} />
        <StatCard label="Healthy" value={d.healthy ?? 0} icon={<CheckCircle style={{ color: EMERALD }} />} />
        <StatCard label="Degraded" value={d.degraded ?? 0} icon={<AlertTriangle style={{ color: AMBER }} />} />
        <StatCard label="Error" value={d.errored ?? 0} icon={<XCircle style={{ color: CRIMSON }} />} />
        <StatCard
          label={`MongoDB ${d.db_latency_ms ? `(${d.db_latency_ms}ms)` : ""}`}
          value={d.db_ok ? "Online" : "OFFLINE"}
        />
      </StatGrid>

      {/* Overall health bar */}
      <Card padding="lg">
        <div className="flex items-center justify-between mb-2">
          <span className="text-xs text-slate-500">Platform Health</span>
          <span className="text-xs font-medium" style={{ color: scoreColor }}>{d.overall_score}%</span>
        </div>
        <MiniBar value={d.overall_score ?? 0} max={100} height={8} />
        <div className="flex items-center gap-4 mt-2 text-[10px] text-slate-400">
          <span>Generated: {(d.generated_at || "").slice(0, 19).replace("T", " ")} UTC</span>
          {d.errors_24h > 0 && <span style={{ color: CRIMSON }}>{d.errors_24h} unresolved errors</span>}
        </div>
      </Card>

      {/* Module grid */}
      {loading ? (
        <div className="flex items-center justify-center gap-2 text-sm text-slate-500 py-8">
          <Spinner size={16} color={TEXT_MUTED} />
          Loading module health...
        </div>
      ) : (
        <div className="space-y-4">
          {errored.length > 0 && (
            <div>
              <div className="text-xs font-semibold uppercase tracking-widest mb-2" style={{ color: CRIMSON }}>Errors — Immediate Action Required</div>
              <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-2">
                {errored.map(m => <ModuleCard key={m.name} module={m} />)}
              </div>
            </div>
          )}
          {degraded.length > 0 && (
            <div>
              <div className="text-xs font-semibold uppercase tracking-widest mb-2" style={{ color: AMBER }}>Degraded — Attention Needed</div>
              <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-2">
                {degraded.map(m => <ModuleCard key={m.name} module={m} />)}
              </div>
            </div>
          )}
          {healthy.length > 0 && (
            <div>
              <div className="text-xs font-semibold uppercase tracking-widest mb-2" style={{ color: EMERALD }}>Healthy</div>
              <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-2">
                {healthy.map(m => <ModuleCard key={m.name} module={m} />)}
              </div>
            </div>
          )}
        </div>
      )}
    </AdministrationLayout>
  );
}
