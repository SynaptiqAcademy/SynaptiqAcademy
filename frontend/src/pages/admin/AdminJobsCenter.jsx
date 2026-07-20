/* eslint-disable */
import React, { useState, useCallback, useEffect } from "react";
import { RefreshCw, Play, Pause, RotateCcw, X, FileText, ChevronDown, ChevronRight } from "lucide-react";
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

const STATUS_COLORS = {
  running:   "text-blue-400 border-blue-700",
  pending:   "text-yellow-400 border-yellow-700",
  completed: "text-green-400 border-green-700",
  failed:    "text-red-400 border-red-700",
  paused:    "text-slate-400 border-slate-600",
  cancelled: "text-slate-500 border-slate-700",
};

function JobRow({ job, onRefresh }) {
  const [expanded, setExpanded] = useState(false);
  const [busy, setBusy] = useState(false);

  const act = async (action) => {
    setBusy(true);
    try { await api.patch(`/admin/x/jobs/${job.id}`, { action }); onRefresh(); }
    catch (e) { console.error(e); }
    finally { setBusy(false); }
  };

  return (
    <>
      <tr className="border-t border-[#1a3050] hover:bg-[#1a3050]/30 cursor-pointer" onClick={() => setExpanded(v => !v)}>
        <td className="px-3 py-2">
          {expanded ? <ChevronDown size={12} className="text-slate-400" /> : <ChevronRight size={12} className="text-slate-400" />}
        </td>
        <td className="px-3 py-2 font-mono text-white text-xs">{job.kind}</td>
        <td className="px-3 py-2">
          <span className={`text-[10px] px-2 py-0.5 border ${STATUS_COLORS[job.status] || "text-slate-400 border-slate-700"}`}>
            {job.status?.toUpperCase()}
          </span>
        </td>
        <td className="px-3 py-2 text-xs text-slate-400">{job.retry_count ?? 0}</td>
        <td className="px-3 py-2 text-xs text-slate-500">{(job.created_at || "").slice(0, 16)}</td>
        <td className="px-3 py-2 text-xs text-slate-500">{job.triggered_by || "system"}</td>
        <td className="px-3 py-2">
          <div className="flex gap-1" onClick={e => e.stopPropagation()}>
            {job.status === "running" && (
              <button onClick={() => act("pause")} disabled={busy} title="Pause" className="p-1 text-slate-400 hover:text-yellow-400">
                <Pause size={12} />
              </button>
            )}
            {job.status === "paused" && (
              <button onClick={() => act("resume")} disabled={busy} title="Resume" className="p-1 text-slate-400 hover:text-green-400">
                <Play size={12} />
              </button>
            )}
            {job.status === "failed" && (
              <button onClick={() => act("retry")} disabled={busy} title="Retry" className="p-1 text-slate-400 hover:text-blue-400">
                <RotateCcw size={12} />
              </button>
            )}
            {["pending", "running"].includes(job.status) && (
              <button onClick={() => act("cancel")} disabled={busy} title="Cancel" className="p-1 text-slate-400 hover:text-red-400">
                <X size={12} />
              </button>
            )}
          </div>
        </td>
      </tr>
      {expanded && (
        <tr className="border-t border-[#1a3050] bg-[#080f1f]">
          <td colSpan={7} className="px-4 py-3">
            <div className="text-xs text-slate-400 mb-2 font-medium">Job Logs</div>
            {(job.logs || []).length === 0 ? (
              <div className="text-xs text-slate-500">No logs</div>
            ) : (
              <div className="space-y-1 max-h-40 overflow-y-auto">
                {(job.logs || []).map((l, i) => (
                  <div key={i} className="flex gap-3 text-[11px]">
                    <span className="text-slate-500 shrink-0">{(l.ts || "").slice(11, 19)}</span>
                    <span className="text-slate-300">{l.msg}</span>
                  </div>
                ))}
              </div>
            )}
            {job.params && Object.keys(job.params).length > 0 && (
              <div className="mt-2 text-xs text-slate-500">
                Params: <span className="text-slate-300 font-mono">{JSON.stringify(job.params)}</span>
              </div>
            )}
          </td>
        </tr>
      )}
    </>
  );
}

const JOB_TYPES = [
  "orcid_sync","openalex_sync","email_batch","notification_batch",
  "analytics_aggregate","publication_enrichment","search_reindex",
  "data_cleanup","platform_audit","citation_snapshot",
];

export default function AdminJobsCenter() {
  const [status, setStatus] = useState("");
  const [kind, setKind]     = useState("");
  const [page, setPage]     = useState(1);
  const [triggerKind, setTriggerKind] = useState("orcid_sync");
  const [triggering, setTriggering]   = useState(false);
  const [triggerMsg, setTriggerMsg]   = useState("");

  const { data: stats, loading: sLoading, refetch: refStats } = useX("jobs/stats");
  const { data: jobs,  loading: jLoading, refetch: refJobs  } = useX("jobs", { status, kind, page, limit: 30 });

  const refetchAll = () => { refStats(); refJobs(); };

  const trigger = async () => {
    setTriggering(true); setTriggerMsg("");
    try {
      const r = await api.post("/admin/x/jobs/trigger", { kind: triggerKind });
      setTriggerMsg(`Enqueued: ${r.data.job_id}`);
      setTimeout(() => { setTriggerMsg(""); refetchAll(); }, 2000);
    } catch (e) { setTriggerMsg(e?.response?.data?.detail || "Error"); }
    finally { setTriggering(false); }
  };

  const s = stats || {};
  const items = jobs?.items || [];
  const total = jobs?.total || 0;

  return (
    <AdministrationLayout
      title="Background Jobs & Automation Center"
      subtitle="Visibility into all background processing, retry and cancel controls"
      actions={
        <button onClick={refetchAll} className="p-1.5 bg-[#0F2847] border border-[#1a3050] text-slate-400 hover:text-white">
          <RefreshCw size={14} className={(sLoading || jLoading) ? "animate-spin" : ""} />
        </button>
      }
    >

      {/* Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-7 gap-3">
        {[
          { label: "Total", value: s.total, color: "text-white" },
          { label: "Running", value: s.running, color: "text-blue-400" },
          { label: "Pending", value: s.pending, color: "text-yellow-400" },
          { label: "Completed", value: s.completed, color: "text-green-400" },
          { label: "Failed", value: s.failed, color: "text-red-400" },
          { label: "Last 24h", value: s.recent_24h, color: "text-white" },
          { label: "Success Rate", value: `${s.success_rate_pct ?? 0}%`, color: s.success_rate_pct >= 90 ? "text-green-400" : "text-yellow-400" },
        ].map(({ label, value, color }) => (
          <div key={label} className="bg-[#0F2847] border border-[#1a3050] p-3">
            <div className={`text-xl font-bold ${color}`}>{value ?? 0}</div>
            <div className="text-[10px] text-slate-500">{label}</div>
          </div>
        ))}
      </div>

      {/* By kind */}
      {(s.by_kind || []).length > 0 && (
        <div className="bg-[#0F2847] border border-[#1a3050] p-4">
          <div className="text-xs text-slate-500 font-medium mb-3">By Kind</div>
          <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-5 gap-2">
            {s.by_kind.map(k => (
              <div key={k.kind} className="flex items-center justify-between gap-2 text-xs">
                <span className="text-slate-300 font-mono truncate">{k.kind}</span>
                <span className="text-white">{k.count}</span>
                {k.failed > 0 && <span className="text-red-400">({k.failed} failed)</span>}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Trigger job */}
      <div className="bg-[#0F2847] border border-[#1a3050] p-4">
        <div className="text-xs text-slate-500 font-medium mb-3">Trigger Background Job</div>
        <div className="flex gap-2 items-center">
          <select value={triggerKind} onChange={e => setTriggerKind(e.target.value)}
            className="text-xs bg-[#0B1C35] border border-[#1a3050] text-slate-300 px-2 py-1.5 flex-1 max-w-xs">
            {JOB_TYPES.map(t => <option key={t} value={t}>{t}</option>)}
          </select>
          <button onClick={trigger} disabled={triggering}
            className="flex items-center gap-1.5 text-xs bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white px-3 py-1.5">
            <Play size={11} /> {triggering ? "Enqueuing..." : "Trigger Now"}
          </button>
          {triggerMsg && <span className="text-xs text-slate-300">{triggerMsg}</span>}
        </div>
      </div>

      {/* Filters */}
      <div className="flex gap-2 flex-wrap">
        <select value={status} onChange={e => { setStatus(e.target.value); setPage(1); }}
          className="text-xs bg-[#0F2847] border border-[#1a3050] text-slate-300 px-2 py-1.5">
          <option value="">All statuses</option>
          {["pending","running","completed","failed","paused","cancelled"].map(s => <option key={s} value={s}>{s}</option>)}
        </select>
        <select value={kind} onChange={e => { setKind(e.target.value); setPage(1); }}
          className="text-xs bg-[#0F2847] border border-[#1a3050] text-slate-300 px-2 py-1.5">
          <option value="">All kinds</option>
          {JOB_TYPES.map(t => <option key={t} value={t}>{t}</option>)}
        </select>
        <span className="text-xs text-slate-500 self-center">{total} jobs</span>
      </div>

      {/* Jobs table */}
      <div className="bg-[#0F2847] border border-[#1a3050] overflow-x-auto">
        <table className="w-full text-xs text-slate-300">
          <thead className="text-slate-500 border-b border-[#1a3050]">
            <tr>
              <th className="px-3 py-2 w-6" />
              <th className="text-left px-3 py-2 font-medium">Kind</th>
              <th className="text-left px-3 py-2 font-medium">Status</th>
              <th className="text-left px-3 py-2 font-medium">Retries</th>
              <th className="text-left px-3 py-2 font-medium">Created</th>
              <th className="text-left px-3 py-2 font-medium">Triggered By</th>
              <th className="px-3 py-2 font-medium">Actions</th>
            </tr>
          </thead>
          <tbody>
            {jLoading && <tr><td colSpan={7} className="px-3 py-8 text-center text-slate-500">Loading...</td></tr>}
            {!jLoading && items.map(j => <JobRow key={j.id} job={j} onRefresh={refetchAll} />)}
            {!jLoading && items.length === 0 && (
              <tr><td colSpan={7} className="px-3 py-8 text-center text-slate-500">No jobs found</td></tr>
            )}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      {total > 30 && (
        <div className="flex items-center gap-2">
          <button onClick={() => setPage(p => Math.max(1, p - 1))} disabled={page === 1}
            className="text-xs px-2 py-1 bg-[#0F2847] border border-[#1a3050] text-slate-400 hover:text-white disabled:opacity-50">← Prev</button>
          <span className="text-xs text-slate-500">Page {page} of {Math.ceil(total / 30)}</span>
          <button onClick={() => setPage(p => p + 1)} disabled={page * 30 >= total}
            className="text-xs px-2 py-1 bg-[#0F2847] border border-[#1a3050] text-slate-400 hover:text-white disabled:opacity-50">Next →</button>
        </div>
      )}
    </AdministrationLayout>
  );
}
