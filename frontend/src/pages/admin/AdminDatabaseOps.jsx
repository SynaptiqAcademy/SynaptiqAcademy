/* eslint-disable */
import React, { useState, useCallback, useEffect } from "react";
import { Database, HardDrive, AlertTriangle, CheckCircle, RefreshCw, Activity } from "lucide-react";
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

export default function AdminDatabaseOps() {
  const { data: overview, loading: ovLoad, refetch: refOv } = useAOS("db/overview");
  const { data: integrity, loading: intLoad, refetch: refInt } = useAOS("db/integrity");
  const { data: health, loading: hlLoad, refetch: refHl } = useAOS("db/health");

  const loading = ovLoad || intLoad || hlLoad;
  const refetchAll = () => { refOv(); refInt(); refHl(); };

  const ov  = overview   || {};
  const int = integrity  || {};
  const h   = health     || {};

  const scoreColor = (s) => s >= 80 ? "text-green-400" : s >= 50 ? "text-yellow-400" : "text-red-400";

  return (
    <AdministrationLayout
      title="Database Operations Center"
      subtitle="MongoDB cluster health, collection stats, and integrity"
      actions={
        <button onClick={refetchAll} className="p-1.5 bg-[#0F2847] border border-[#1a3050] text-slate-400 hover:text-white">
          <RefreshCw size={14} className={loading ? "animate-spin" : ""} />
        </button>
      }
    >

      {/* DB Health */}
      {!hlLoad && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <div className="bg-[#0F2847] border border-[#1a3050] p-4 flex items-center gap-3">
            {h.ok ? (
              <CheckCircle size={20} className="text-green-400 flex-shrink-0" />
            ) : (
              <AlertTriangle size={20} className="text-red-400 flex-shrink-0" />
            )}
            <div>
              <div className="text-sm font-bold text-white">{h.ok ? "Connected" : "Disconnected"}</div>
              <div className="text-xs text-slate-400">Database Status</div>
            </div>
          </div>
          <div className="bg-[#0F2847] border border-[#1a3050] p-4">
            <div className={`text-2xl font-bold ${scoreColor(h.health_score || 0)}`}>{h.health_score ?? "—"}</div>
            <div className="text-xs text-slate-400">Health Score</div>
          </div>
          <div className="bg-[#0F2847] border border-[#1a3050] p-4">
            <div className="text-2xl font-bold text-white">{h.latency_ms ?? "—"} ms</div>
            <div className="text-xs text-slate-400">Ping Latency</div>
          </div>
          <div className="bg-[#0F2847] border border-[#1a3050] p-4">
            <div className="text-2xl font-bold text-white">{h.server_info?.connections ?? "—"}</div>
            <div className="text-xs text-slate-400">Active Connections</div>
            {h.server_info?.version && (
              <div className="text-[10px] text-slate-500 mt-1">MongoDB {h.server_info.version}</div>
            )}
          </div>
        </div>
      )}

      {/* Storage */}
      {!ovLoad && !ov.error && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <div className="bg-[#0F2847] border border-[#1a3050] p-4">
            <div className="flex items-center gap-2 mb-1">
              <HardDrive size={14} className="text-blue-400" />
              <span className="text-xs text-slate-400">Storage</span>
            </div>
            <div className="text-xl font-bold text-white">{ov.storage_size_mb} MB</div>
          </div>
          <div className="bg-[#0F2847] border border-[#1a3050] p-4">
            <div className="flex items-center gap-2 mb-1">
              <Database size={14} className="text-purple-400" />
              <span className="text-xs text-slate-400">Data Size</span>
            </div>
            <div className="text-xl font-bold text-white">{ov.data_size_mb} MB</div>
          </div>
          <div className="bg-[#0F2847] border border-[#1a3050] p-4">
            <div className="flex items-center gap-2 mb-1">
              <Activity size={14} className="text-green-400" />
              <span className="text-xs text-slate-400">Collections</span>
            </div>
            <div className="text-xl font-bold text-white">{ov.total_collections}</div>
          </div>
          <div className="bg-[#0F2847] border border-[#1a3050] p-4">
            <div className="flex items-center gap-2 mb-1">
              <Activity size={14} className="text-yellow-400" />
              <span className="text-xs text-slate-400">Indexes</span>
            </div>
            <div className="text-xl font-bold text-white">{ov.total_indexes}</div>
            <div className="text-[10px] text-slate-500">{ov.index_size_mb} MB index size</div>
          </div>
        </div>
      )}

      {/* Integrity */}
      {!intLoad && (
        <div className="bg-[#0F2847] border border-[#1a3050] p-4">
          <div className="flex items-center justify-between mb-3">
            <div className="text-sm font-semibold text-white">Data Integrity</div>
            <div className="flex items-center gap-2">
              <div className={`text-2xl font-bold ${scoreColor(int.integrity_score || 0)}`}>
                {int.integrity_score ?? "—"}
              </div>
              <div className="text-xs text-slate-400">/ 100</div>
            </div>
          </div>
          <div className="text-[10px] text-slate-500 mb-3">Scanned at {(int.scanned_at || "").slice(0, 19)}</div>
          {(int.issues || []).length === 0 ? (
            <div className="flex items-center gap-2 text-green-400 text-sm">
              <CheckCircle size={14} />
              No integrity issues detected
            </div>
          ) : (
            <div className="space-y-2">
              {(int.issues || []).map((issue, i) => (
                <div key={i} className="flex items-start gap-3 p-2 bg-yellow-900/20 border border-yellow-700/40">
                  <AlertTriangle size={12} className="text-yellow-400 flex-shrink-0 mt-0.5" />
                  <div>
                    <div className="text-xs text-white">{issue.type?.replace(/_/g, " ")}: {issue.count} records</div>
                    <div className="text-[10px] text-slate-400">{issue.action}</div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Collection list */}
      {!ovLoad && (ov.collections || []).length > 0 && (
        <div className="bg-[#0F2847] border border-[#1a3050]">
          <div className="px-4 py-3 border-b border-[#1a3050]">
            <div className="text-sm font-semibold text-white">Collections ({ov.total_collections})</div>
          </div>
          <div className="overflow-y-auto max-h-96">
            <table className="w-full text-xs text-slate-300">
              <thead className="text-slate-500 border-b border-[#1a3050] sticky top-0 bg-[#0F2847]">
                <tr>
                  <th className="text-left px-4 py-2 font-medium">Collection</th>
                  <th className="text-right px-4 py-2 font-medium">Documents</th>
                </tr>
              </thead>
              <tbody>
                {(ov.collections || []).map((c) => (
                  <tr key={c.collection} className="border-t border-[#1a3050] hover:bg-[#1a3050]/30">
                    <td className="px-4 py-2 font-mono">{c.collection}</td>
                    <td className="px-4 py-2 text-right text-white">
                      {c.count < 0 ? "error" : c.count.toLocaleString()}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </AdministrationLayout>
  );
}
