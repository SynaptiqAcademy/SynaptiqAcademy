import React, { useState, useCallback, useEffect } from "react";
import { RefreshCw, HardDrive, AlertTriangle, Archive } from "lucide-react";
import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer, Legend } from "recharts";
import api from "@/lib/api";
import { NAVY, CRIMSON, AMBER } from "@/lib/tokens";
import { AdministrationLayout } from "@/layouts";
import { Card, Button, StatCard, StatGrid, DataTable } from "@/components/ds";

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

const PRIORITY_ACCENT = {
  high:   CRIMSON,
  medium: AMBER,
  low:    "#3B82F6",
};

const PRIORITY_TEXT = {
  high:   "text-red-700",
  medium: "text-amber-700",
  low:    "text-blue-700",
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

  const orphanRows = [
    ...(orph?.no_owner || []).map(f => ({...f, reason: "no owner"})),
    ...(orph?.deleted_user || []).map(f => ({...f, reason: "deleted user"})),
  ];

  const orphanColumns = [
    { key: "filename", label: "Filename", maxWidth: 180, render: (v) => <span className="truncate block">{v || "unknown"}</span> },
    { key: "size_bytes", label: "Size", align: "right", render: (v) => <span className="text-slate-500">{Math.round((v || 0) / 1024)}K</span> },
    { key: "reason", label: "Reason", render: (v) => <span className="text-red-600">{v}</span> },
  ];

  const largeColumns = [
    { key: "filename", label: "Filename", maxWidth: 220, render: (v) => <span className="truncate block font-medium text-slate-900">{v || "unknown"}</span> },
    { key: "size_mb", label: "Size", align: "right", render: (v) => <span className="font-mono">{v} MB</span> },
    { key: "content_type", label: "Type", maxWidth: 120, render: (v) => <span className="text-slate-500 truncate block">{v || "—"}</span> },
    { key: "created_at", label: "Uploaded", render: (v) => <span className="text-slate-500">{(v || "").slice(0, 10)}</span> },
  ];

  return (
    <AdministrationLayout
      title="Storage & File Governance Center"
      subtitle="Orphan detection, large file analysis, and cleanup recommendations"
      actions={
        <Button variant="ghost" size="icon" onClick={refetchAll} aria-label="Refresh">
          <RefreshCw size={14} className={loading ? "animate-spin" : ""} />
        </Button>
      }
    >
      <div className="flex flex-col gap-6">
        {/* Overview stats */}
        <StatGrid cols={6}>
          <StatCard label="Total Files" value={(o.total_files || 0).toLocaleString()} />
          <StatCard label="Total Storage" value={`${o.total_mb ?? 0} MB`} />
          <StatCard label="Avg File Size" value={`${o.avg_kb ?? 0} KB`} />
          <StatCard label="New (30d)" value={o.new_files_30d ?? 0} />
          <StatCard label="PDFs Attached" value={o.publications_with_pdf ?? 0} />
          <StatCard label="File Types" value={(o.by_type || []).length} />
        </StatGrid>

        {/* Recommendations */}
        {(recs?.recommendations || []).length > 0 && (
          <div className="space-y-2">
            <div className="text-xs font-semibold uppercase tracking-widest text-slate-500">Cleanup Recommendations</div>
            {recs.recommendations.map((r, i) => (
              <Card key={i} accent={PRIORITY_ACCENT[r.priority] || PRIORITY_ACCENT.low} padding="sm" className={`flex items-start gap-3 text-xs ${PRIORITY_TEXT[r.priority] || PRIORITY_TEXT.low}`}>
                <AlertTriangle size={12} className="flex-shrink-0 mt-0.5" />
                <div>
                  <span className="font-medium uppercase text-[10px] mr-2">{r.priority}</span>
                  {r.description}
                </div>
              </Card>
            ))}
          </div>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          {/* By type pie */}
          {byType.length > 0 && (
            <Card padding="md">
              <div className="text-xs text-slate-500 font-medium mb-3">Storage by File Type</div>
              <ResponsiveContainer width="100%" height={200}>
                <PieChart>
                  <Pie data={byType} dataKey="mb" nameKey="type" cx="50%" cy="50%" outerRadius={70} label={false}>
                    {byType.map((t, i) => <Cell key={i} fill={t.fill} />)}
                  </Pie>
                  <Tooltip contentStyle={{ background: "#ffffff", border: "1px solid #e2e8f0", fontSize: 11 }}
                    formatter={(v) => [`${v} MB`]} />
                  <Legend wrapperStyle={{ fontSize: 10, color: "#64748b" }} />
                </PieChart>
              </ResponsiveContainer>
            </Card>
          )}

          {/* Orphan files */}
          <Card padding="none">
            <div className="flex items-center gap-2 px-4 py-3 border-b border-slate-200">
              <AlertTriangle size={14} className="text-red-500" />
              <span className="text-sm font-semibold text-slate-800">Orphan Files</span>
              {orph && <span className="text-xs text-red-600">({orph.total_orphan_count ?? 0} total, {orph.total_orphan_mb ?? 0} MB)</span>}
            </div>
            <div className="max-h-52 overflow-y-auto">
              <DataTable
                columns={orphanColumns}
                rows={orphanRows}
                loading={orL}
                emptyNode={<div className="px-3 py-6 text-center text-emerald-600 text-xs">No orphaned files detected</div>}
              />
            </div>
          </Card>
        </div>

        {/* Large files */}
        <Card padding="none">
          <div className="flex items-center gap-2 px-4 py-3 border-b border-slate-200">
            <Archive size={14} className="text-amber-500" />
            <span className="text-sm font-semibold text-slate-800">Largest Files</span>
          </div>
          <DataTable
            columns={largeColumns}
            rows={(large?.items || []).slice(0, 15)}
            loading={lgL}
            emptyNode={<div className="px-3 py-6 text-center text-slate-400 text-xs">No files found</div>}
          />
        </Card>
      </div>
    </AdministrationLayout>
  );
}
