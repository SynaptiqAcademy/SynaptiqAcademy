/* eslint-disable */
import React, { useState, useCallback, useEffect } from "react";
import { RefreshCw, CheckCircle, AlertTriangle, XCircle, ExternalLink } from "lucide-react";
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

const STATUS_ICONS = {
  healthy:  { Icon: CheckCircle, color: "text-green-400" },
  degraded: { Icon: AlertTriangle, color: "text-yellow-400" },
  error:    { Icon: XCircle, color: "text-red-400" },
};

const STATUS_BORDER = {
  healthy:  "border-green-700/40 bg-green-900/10 hover:border-green-600",
  degraded: "border-yellow-700/40 bg-yellow-900/10 hover:border-yellow-600",
  error:    "border-red-700/40 bg-red-900/10 hover:border-red-600",
};

function ModuleCard({ module }) {
  const { Icon, color } = STATUS_ICONS[module.status] || STATUS_ICONS.healthy;
  const borderClass = STATUS_BORDER[module.status] || STATUS_BORDER.healthy;

  return (
    <a href={module.route} className={`block border p-3 transition-colors cursor-pointer group ${borderClass}`}>
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <Icon size={14} className={color} />
          <span className="text-xs font-medium text-white">{module.name}</span>
        </div>
        <ExternalLink size={10} className="text-slate-600 group-hover:text-slate-400 transition-colors" />
      </div>
      <div className="flex items-center gap-3 text-[10px] text-slate-500">
        <span>{(module.records || 0).toLocaleString()} records</span>
        {module.errors_24h > 0 && (
          <span className="text-red-400">{module.errors_24h} errors/24h</span>
        )}
        {!module.env_ok && (
          <span className="text-yellow-400">env missing</span>
        )}
      </div>
    </a>
  );
}

export default function AdminCommandMap() {
  const { data, loading, refetch } = useX("command-map");

  const d = data || {};
  const modules = d.modules || [];
  const healthy  = modules.filter(m => m.status === "healthy");
  const degraded = modules.filter(m => m.status === "degraded");
  const errored  = modules.filter(m => m.status === "error");

  const scoreColor = d.overall_score >= 90 ? "text-green-400" : d.overall_score >= 70 ? "text-yellow-400" : "text-red-400";

  return (
    <AdministrationLayout
      title="Platform Command Map"
      subtitle={`Real-time health status of all ${d.module_count || 20} platform modules`}
      actions={
        <button onClick={refetch} className="p-1.5 bg-[#0F2847] border border-[#1a3050] text-slate-400 hover:text-white">
          <RefreshCw size={14} className={loading ? "animate-spin" : ""} />
        </button>
      }
    >

      {/* Header stats */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
        <div className="bg-[#0F2847] border border-[#1a3050] p-4">
          <div className={`text-3xl font-bold ${scoreColor}`}>{d.overall_score ?? "—"}</div>
          <div className="text-xs text-slate-400">Platform Score</div>
        </div>
        <div className="bg-[#0F2847] border border-green-700/30 bg-green-900/10 p-4">
          <div className="text-3xl font-bold text-green-400">{d.healthy ?? 0}</div>
          <div className="text-xs text-slate-400">Healthy</div>
        </div>
        <div className="bg-[#0F2847] border border-yellow-700/30 bg-yellow-900/10 p-4">
          <div className="text-3xl font-bold text-yellow-400">{d.degraded ?? 0}</div>
          <div className="text-xs text-slate-400">Degraded</div>
        </div>
        <div className="bg-[#0F2847] border border-red-700/30 bg-red-900/10 p-4">
          <div className="text-3xl font-bold text-red-400">{d.errored ?? 0}</div>
          <div className="text-xs text-slate-400">Error</div>
        </div>
        <div className="bg-[#0F2847] border border-[#1a3050] p-4">
          <div className={`text-xl font-bold ${d.db_ok ? "text-green-400" : "text-red-400"}`}>
            {d.db_ok ? "Online" : "OFFLINE"}
          </div>
          <div className="text-xs text-slate-400">MongoDB {d.db_latency_ms ? `(${d.db_latency_ms}ms)` : ""}</div>
        </div>
      </div>

      {/* Overall health bar */}
      <div className="bg-[#0F2847] border border-[#1a3050] p-4">
        <div className="flex items-center justify-between mb-2">
          <span className="text-xs text-slate-400">Platform Health</span>
          <span className={`text-xs font-medium ${scoreColor}`}>{d.overall_score}%</span>
        </div>
        <div className="h-2 bg-[#1a3050] rounded-full overflow-hidden">
          <div className={`h-full transition-all ${d.overall_score >= 90 ? "bg-green-500" : d.overall_score >= 70 ? "bg-yellow-500" : "bg-red-500"}`}
            style={{ width: `${d.overall_score ?? 0}%` }} />
        </div>
        <div className="flex items-center gap-4 mt-2 text-[10px] text-slate-500">
          <span>Generated: {(d.generated_at || "").slice(0, 19).replace("T", " ")} UTC</span>
          {d.errors_24h > 0 && <span className="text-red-400">{d.errors_24h} unresolved errors</span>}
        </div>
      </div>

      {/* Module grid */}
      {loading ? (
        <div className="text-sm text-slate-500 text-center py-8">Loading module health...</div>
      ) : (
        <div className="space-y-4">
          {errored.length > 0 && (
            <div>
              <div className="text-xs font-semibold uppercase tracking-widest text-red-400 mb-2">Errors — Immediate Action Required</div>
              <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-2">
                {errored.map(m => <ModuleCard key={m.name} module={m} />)}
              </div>
            </div>
          )}
          {degraded.length > 0 && (
            <div>
              <div className="text-xs font-semibold uppercase tracking-widest text-yellow-400 mb-2">Degraded — Attention Needed</div>
              <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-2">
                {degraded.map(m => <ModuleCard key={m.name} module={m} />)}
              </div>
            </div>
          )}
          {healthy.length > 0 && (
            <div>
              <div className="text-xs font-semibold uppercase tracking-widest text-green-400 mb-2">Healthy</div>
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
