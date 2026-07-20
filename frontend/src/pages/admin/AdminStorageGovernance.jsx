import React, { useState, useCallback, useEffect } from "react";
import { RefreshCw, HardDrive, AlertTriangle, Archive } from "lucide-react";
import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer, Legend } from "recharts";
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

const PIE_COLORS = ["#3b82f6","#8b5cf6","#10b981","#f59e0b","#ef4444","#6366f1","#ec4899","#14b8a6"];

const PRIORITY_STYLE = {
  high:   "text-red-400 border-red-700 bg-red-900/20",
  medium: "text-yellow-400 border-yellow-700 bg-yellow-900/20",
  low:    "text-blue-400 border-blue-700 bg-blue-900/20",
};

export default function AdminStorageGovernance() {
  const { data: ov,   loading: ovL,  refetch: refOv   } = useX("storage/overview");
  const { data: orph, loading: orL,  refetch: refOrph  } = useX("storage/orphans");
  const { data: large, loading: lgL, refetch: refLarge } = useX("storage/large-files");
  const { data: recs,  loading: rcL, refetch: refRecs  } = useX("storage/recommendations");

  const refetchAll = () => { refOv(); refOrph(); refLarge(); refRecs(); };
  const loading = ovL || orL || lgL || rcL;

  const o = ov || {};
  const byType = (o.by_type || []).map((t, i) => ({ ...t, fill: PIE_COLORS[i % PIE_COLORS.length] }));

  return (
    <AdministrationLayout
      title="Storage & File Governance Center"
      subtitle="Orphan detection, large file analysis, and cleanup recommendations"
      actions={
        <button onClick={refetchAll} className="p-1.5 bg-[#0F2847] border border-[#1a3050] text-slate-400 hover:text-white">
          <RefreshCw size={14} className={loading ? "animate-spin" : ""} />
        </button>
      }
    >

      {/* Overview stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-3">
        {[
          { label: "Total Files", value: (o.total_files || 0).toLocaleString(), color: "text-white" },
          { label: "Total Storage", value: `${o.total_mb ?? 0} MB`, color: "text-blue-400" },
          { label: "Avg File Size", value: `${o.avg_kb ?? 0} KB`, color: "text-slate-300" },
          { label: "New (30d)", value: o.new_files_30d ?? 0, color: "text-green-400" },
          { label: "PDFs Attached", value: o.publications_with_pdf ?? 0, color: "text-purple-400" },
          { label: "File Types", value: (o.by_type || []).length, color: "text-slate-300" },
        ].map(({ label, value, color }) => (
          <div key={label} className="bg-[#0F2847] border border-[#1a3050] p-4">
            <div className={`text-xl font-bold ${color}`}>{value}</div>
            <div className="text-xs text-slate-400">{label}</div>
          </div>
        ))}
      </div>

      {/* Recommendations */}
      {(recs?.recommendations || []).length > 0 && (
        <div className="space-y-2">
          <div className="text-xs font-semibold uppercase tracking-widest text-slate-500">Cleanup Recommendations</div>
          {recs.recommendations.map((r, i) => (
            <div key={i} className={`flex items-start gap-3 border p-3 text-xs ${PRIORITY_STYLE[r.priority] || PRIORITY_STYLE.low}`}>
              <AlertTriangle size={12} className="flex-shrink-0 mt-0.5" />
              <div>
                <span className="font-medium uppercase text-[10px] mr-2">{r.priority}</span>
                {r.description}
              </div>
            </div>
          ))}
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* By type pie */}
        {byType.length > 0 && (
          <div className="bg-[#0F2847] border border-[#1a3050] p-4">
            <div className="text-xs text-slate-500 font-medium mb-3">Storage by File Type</div>
            <ResponsiveContainer width="100%" height={200}>
              <PieChart>
                <Pie data={byType} dataKey="mb" nameKey="type" cx="50%" cy="50%" outerRadius={70} label={false}>
                  {byType.map((t, i) => <Cell key={i} fill={t.fill} />)}
                </Pie>
                <Tooltip contentStyle={{ background: "#0B1C35", border: "1px solid #1a3050", fontSize: 11 }}
                  formatter={(v) => [`${v} MB`]} />
                <Legend wrapperStyle={{ fontSize: 10, color: "#94a3b8" }} />
              </PieChart>
            </ResponsiveContainer>
          </div>
        )}

        {/* Orphan files */}
        <div className="bg-[#0F2847] border border-[#1a3050]">
          <div className="flex items-center gap-2 px-4 py-3 border-b border-[#1a3050]">
            <AlertTriangle size={14} className="text-red-400" />
            <span className="text-sm font-semibold text-white">Orphan Files</span>
            {orph && <span className="text-xs text-red-400">({orph.total_orphan_count ?? 0} total, {orph.total_orphan_mb ?? 0} MB)</span>}
          </div>
          <div className="overflow-y-auto max-h-52">
            <table className="w-full text-xs text-slate-300">
              <thead className="text-slate-500 border-b border-[#1a3050]">
                <tr>
                  <th className="text-left px-3 py-2 font-medium">Filename</th>
                  <th className="text-right px-3 py-2 font-medium">Size</th>
                  <th className="text-left px-3 py-2 font-medium">Reason</th>
                </tr>
              </thead>
              <tbody>
                {[
                  ...(orph?.no_owner || []).map(f => ({...f, reason: "no owner"})),
                  ...(orph?.deleted_user || []).map(f => ({...f, reason: "deleted user"})),
                ].map((f, i) => (
                  <tr key={i} className="border-t border-[#1a3050] hover:bg-[#1a3050]/30">
                    <td className="px-3 py-1.5 max-w-[180px] truncate text-slate-300">{f.filename || "unknown"}</td>
                    <td className="px-3 py-1.5 text-right text-slate-400">{Math.round((f.size_bytes || 0) / 1024)}K</td>
                    <td className="px-3 py-1.5 text-red-400">{f.reason}</td>
                  </tr>
                ))}
                {!orL && (orph?.no_owner || []).length === 0 && (orph?.deleted_user || []).length === 0 && (
                  <tr><td colSpan={3} className="px-3 py-6 text-center text-green-400">No orphaned files detected</td></tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      {/* Large files */}
      <div className="bg-[#0F2847] border border-[#1a3050]">
        <div className="flex items-center gap-2 px-4 py-3 border-b border-[#1a3050]">
          <Archive size={14} className="text-yellow-400" />
          <span className="text-sm font-semibold text-white">Largest Files</span>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-xs text-slate-300">
            <thead className="text-slate-500 border-b border-[#1a3050]">
              <tr>
                <th className="text-left px-3 py-2 font-medium">Filename</th>
                <th className="text-right px-3 py-2 font-medium">Size</th>
                <th className="text-left px-3 py-2 font-medium">Type</th>
                <th className="text-left px-3 py-2 font-medium">Uploaded</th>
              </tr>
            </thead>
            <tbody>
              {(large?.items || []).slice(0, 15).map((f, i) => (
                <tr key={i} className="border-t border-[#1a3050] hover:bg-[#1a3050]/30">
                  <td className="px-3 py-2 max-w-[220px] truncate text-white">{f.filename || "unknown"}</td>
                  <td className="px-3 py-2 text-right font-mono">{f.size_mb} MB</td>
                  <td className="px-3 py-2 text-slate-400 max-w-[120px] truncate">{f.content_type || "—"}</td>
                  <td className="px-3 py-2 text-slate-500">{(f.created_at || "").slice(0, 10)}</td>
                </tr>
              ))}
              {!lgL && (large?.items || []).length === 0 && (
                <tr><td colSpan={4} className="px-3 py-6 text-center text-slate-500">No files found</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </AdministrationLayout>
  );
}
