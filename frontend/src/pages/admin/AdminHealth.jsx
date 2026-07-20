import React, { useState, useCallback, useEffect } from "react";
import { CheckCircle, XCircle, Activity, Server, Link, AlertTriangle, RefreshCw } from "lucide-react";
import api from "@/lib/api";
import { NAVY } from "@/lib/tokens";
import { AdministrationLayout } from "@/layouts";

function useAOS(path) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const fetch = useCallback(() => {
    setLoading(true);
    api.get(`/admin/aos/${path}`)
      .then((r) => setData(r.data))
      .catch(() => setData(null))
      .finally(() => setLoading(false));
  }, [path]);
  useEffect(() => { fetch(); }, [fetch]);
  return { data, loading, refetch: fetch };
}

function StatusDot({ ok }) {
  return <span className={`w-2 h-2 rounded-full flex-shrink-0 ${ok ? "bg-green-400" : "bg-red-400"}`} />;
}

function IntegrationRow({ name, config }) {
  return (
    <div className="flex items-center justify-between py-2 border-b border-[#1a3050] last:border-0">
      <div className="flex items-center gap-2">
        <StatusDot ok={config.configured} />
        <span className="text-sm text-slate-300 capitalize">{name.replace(/_/g, " ")}</span>
      </div>
      <span className={`text-xs px-2 py-0.5 ${config.configured ? "text-green-400" : "text-red-400"}`}>
        {config.status}
      </span>
    </div>
  );
}

export default function AdminHealth() {
  const { data: infra,  loading: iLoad,  refetch: refInfra }    = useAOS("health/infrastructure");
  const { data: integ,  loading: igLoad, refetch: refInteg }    = useAOS("health/integrations");
  const { data: incidents, loading: incLoad, refetch: refInc }  = useAOS("health/incidents");
  const { data: prReady, loading: prLoad }                      = useAOS("platform-audit/scores");

  const loading = iLoad || igLoad || incLoad || prLoad;
  const refetchAll = () => { refInfra(); refInteg(); refInc(); };

  const inf = infra || {};
  const ig  = integ || {};
  const score = prReady?.overall_score;
  const scoreColor = score >= 70 ? "text-green-400" : score >= 40 ? "text-yellow-400" : "text-red-400";

  return (
    <AdministrationLayout
      title="Platform Health Center"
      subtitle="Infrastructure, integrations, and incident monitoring"
      actions={
        <button onClick={refetchAll} className="p-1.5 bg-[#0F2847] border border-[#1a3050] text-slate-400 hover:text-white">
          <RefreshCw size={14} className={loading ? "animate-spin" : ""} />
        </button>
      }
    >

      {/* Summary row */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <div className="bg-[#0F2847] border border-[#1a3050] p-4 flex items-center gap-3">
          {inf.database?.ok ? (
            <CheckCircle size={18} className="text-green-400 flex-shrink-0" />
          ) : (
            <XCircle size={18} className="text-red-400 flex-shrink-0" />
          )}
          <div>
            <div className="text-sm font-bold text-white">{inf.database?.ok ? "Healthy" : "Error"}</div>
            <div className="text-xs text-slate-400">Database</div>
          </div>
        </div>
        <div className="bg-[#0F2847] border border-[#1a3050] p-4">
          <div className="text-2xl font-bold text-white">{Math.round(inf.app_uptime_hours || 0)}h</div>
          <div className="text-xs text-slate-400">App Uptime</div>
        </div>
        <div className="bg-[#0F2847] border border-[#1a3050] p-4">
          <div className={`text-2xl font-bold ${scoreColor}`}>{score ?? "—"}</div>
          <div className="text-xs text-slate-400">Platform Score</div>
          {prReady?.audited_at && (
            <div className="text-[10px] text-slate-500">{prReady.audited_at.slice(0, 10)}</div>
          )}
        </div>
        <div className="bg-[#0F2847] border border-[#1a3050] p-4">
          <div className={`text-2xl font-bold ${inf.errors_24h > 5 ? "text-red-400" : "text-green-400"}`}>
            {inf.errors_24h ?? 0}
          </div>
          <div className="text-xs text-slate-400">Errors (24h)</div>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Infrastructure */}
        {!iLoad && (
          <div className="bg-[#0F2847] border border-[#1a3050] p-4">
            <div className="flex items-center gap-2 mb-3">
              <Server size={14} className="text-blue-400" />
              <div className="text-sm font-semibold text-white">Infrastructure</div>
            </div>
            <div className="space-y-2 text-xs">
              {[
                ["Python Version",    inf.python_version],
                ["Platform",         inf.platform],
                ["DB Collections",   inf.database?.collections],
                ["DB Connections",   inf.database?.stats?.connections_current],
                ["DB Uptime",        inf.database?.stats?.uptime_seconds ? `${Math.round(inf.database.stats.uptime_seconds / 3600)}h` : "—"],
                ["App Uptime",       `${inf.app_uptime_hours}h`],
                ["Errors 24h",       inf.errors_24h],
              ].map(([label, value]) => (
                <div key={label} className="flex items-center justify-between border-b border-[#1a3050] pb-1.5">
                  <span className="text-slate-400">{label}</span>
                  <span className="text-white">{value ?? "—"}</span>
                </div>
              ))}
              {inf.database?.stats?.ops_per_second && (
                <div>
                  <div className="text-slate-500 mt-2 mb-1">Database Ops/s</div>
                  {Object.entries(inf.database.stats.ops_per_second).map(([op, count]) => (
                    <div key={op} className="flex justify-between text-[10px] py-0.5">
                      <span className="text-slate-500">{op}</span>
                      <span className="text-slate-300">{count}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}

        {/* Integrations */}
        {!igLoad && (
          <div className="bg-[#0F2847] border border-[#1a3050] p-4">
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2">
                <Link size={14} className="text-purple-400" />
                <div className="text-sm font-semibold text-white">Integrations</div>
              </div>
              <div className="text-xs text-slate-400">
                {ig.configured}/{ig.total} configured · Score: {ig.health_score}
              </div>
            </div>
            <div>
              {Object.entries(ig.integrations || {}).map(([name, config]) => (
                <IntegrationRow key={name} name={name} config={config} />
              ))}
            </div>
            <div className="mt-3 flex items-center gap-2">
              <StatusDot ok={ig.db_reachable} />
              <span className="text-xs text-slate-400">Database reachable: {ig.db_reachable ? "Yes" : "No"}</span>
            </div>
          </div>
        )}
      </div>

      {/* Audit scores detail */}
      {prReady?.scores && (
        <div className="bg-[#0F2847] border border-[#1a3050] p-4">
          <div className="text-sm font-semibold text-white mb-3">Platform Audit Scores</div>
          <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
            {Object.entries(prReady.scores).map(([key, val]) => {
              const color = val >= 70 ? "text-green-400" : val >= 40 ? "text-yellow-400" : "text-red-400";
              const bar   = val >= 70 ? "bg-green-500" : val >= 40 ? "bg-yellow-500" : "bg-red-500";
              return (
                <div key={key}>
                  <div className={`text-xl font-bold ${color}`}>{val}</div>
                  <div className="text-[10px] text-slate-500 mb-1">{key.replace(/_/g, " ")}</div>
                  <div className="h-1.5 bg-[#1a3050] rounded-full overflow-hidden">
                    <div className={`h-full ${bar}`} style={{ width: `${val}%` }} />
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Incidents */}
      {!incLoad && (
        <div className="bg-[#0F2847] border border-[#1a3050]">
          <div className="flex items-center gap-2 px-4 py-3 border-b border-[#1a3050]">
            <AlertTriangle size={14} className="text-yellow-400" />
            <div className="text-sm font-semibold text-white">Recent Incidents</div>
            <span className="text-xs text-slate-500">({(incidents?.items || []).length})</span>
          </div>
          {(incidents?.items || []).length === 0 ? (
            <div className="p-6 text-center text-slate-500 text-sm flex items-center justify-center gap-2">
              <CheckCircle size={14} className="text-green-400" />
              No incidents recorded
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-xs text-slate-300">
                <thead className="text-slate-500 border-b border-[#1a3050]">
                  <tr>
                    {["Severity", "Category", "Message", "Frequency", "Date", "Resolved"].map((h) => (
                      <th key={h} className="text-left px-3 py-2 font-medium">{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {(incidents.items || []).slice(0, 20).map((inc) => (
                    <tr key={inc.id} className="border-t border-[#1a3050] hover:bg-[#1a3050]/30">
                      <td className="px-3 py-2">
                        <span className={`text-[10px] px-1.5 py-0.5 ${
                          inc.severity === "critical" ? "text-red-400" :
                          inc.severity === "high" ? "text-orange-400" :
                          "text-yellow-400"
                        }`}>{inc.severity}</span>
                      </td>
                      <td className="px-3 py-2 text-slate-400">{inc.category}</td>
                      <td className="px-3 py-2 max-w-xs truncate">{inc.message}</td>
                      <td className="px-3 py-2 text-slate-400">{inc.frequency}</td>
                      <td className="px-3 py-2 text-slate-400">{(inc.created_at || "").slice(0, 10)}</td>
                      <td className="px-3 py-2">
                        {inc.resolved ? (
                          <CheckCircle size={12} className="text-green-400" />
                        ) : (
                          <XCircle size={12} className="text-red-400" />
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}
    </AdministrationLayout>
  );
}
