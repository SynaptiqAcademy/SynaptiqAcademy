/* eslint-disable */
import React, { useState, useCallback, useEffect } from "react";
import { RefreshCw, Play, Pause, RotateCcw, X, ChevronDown, ChevronRight } from "lucide-react";
import api from "@/lib/api";
import { EMERALD, AMBER, CRIMSON, INFO, BRD } from "@/lib/tokens";
import { AdministrationLayout } from "@/layouts";
import { Button, Card, StatCard, StatGrid, Badge, FormSelect, Pagination } from "@/components/ds";

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

const STATUS_VARIANT = {
  running:   "info",
  pending:   "warning",
  completed: "success",
  failed:    "danger",
  paused:    "neutral",
  cancelled: "neutral",
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
      <tr className="border-t border-slate-100 hover:bg-slate-50 cursor-pointer" onClick={() => setExpanded(v => !v)}>
        <td className="px-3 py-2">
          {expanded ? <ChevronDown size={12} className="text-slate-400" /> : <ChevronRight size={12} className="text-slate-400" />}
        </td>
        <td className="px-3 py-2 font-mono text-slate-800 text-xs">{job.kind}</td>
        <td className="px-3 py-2">
          <Badge size="sm" variant={STATUS_VARIANT[job.status] || "neutral"}>{job.status?.toUpperCase()}</Badge>
        </td>
        <td className="px-3 py-2 text-xs text-slate-500">{job.retry_count ?? 0}</td>
        <td className="px-3 py-2 text-xs text-slate-400">{(job.created_at || "").slice(0, 16)}</td>
        <td className="px-3 py-2 text-xs text-slate-400">{job.triggered_by || "system"}</td>
        <td className="px-3 py-2">
          <div className="flex gap-1" onClick={e => e.stopPropagation()}>
            {job.status === "running" && (
              <button onClick={() => act("pause")} disabled={busy} title="Pause" className="p-1 text-slate-400 hover:text-amber-600 disabled:opacity-40">
                <Pause size={12} />
              </button>
            )}
            {job.status === "paused" && (
              <button onClick={() => act("resume")} disabled={busy} title="Resume" className="p-1 text-slate-400 hover:text-emerald-600 disabled:opacity-40">
                <Play size={12} />
              </button>
            )}
            {job.status === "failed" && (
              <button onClick={() => act("retry")} disabled={busy} title="Retry" className="p-1 text-slate-400 hover:text-blue-600 disabled:opacity-40">
                <RotateCcw size={12} />
              </button>
            )}
            {["pending", "running"].includes(job.status) && (
              <button onClick={() => act("cancel")} disabled={busy} title="Cancel" className="p-1 text-slate-400 hover:text-red-600 disabled:opacity-40">
                <X size={12} />
              </button>
            )}
          </div>
        </td>
      </tr>
      {expanded && (
        <tr className="border-t border-slate-100 bg-slate-50">
          <td colSpan={7} className="px-4 py-3">
            <div className="text-xs text-slate-500 mb-2 font-medium">Job Logs</div>
            {(job.logs || []).length === 0 ? (
              <div className="text-xs text-slate-400">No logs</div>
            ) : (
              <div className="space-y-1 max-h-40 overflow-y-auto">
                {(job.logs || []).map((l, i) => (
                  <div key={i} className="flex gap-3 text-[11px]">
                    <span className="text-slate-400 shrink-0">{(l.ts || "").slice(11, 19)}</span>
                    <span className="text-slate-600">{l.msg}</span>
                  </div>
                ))}
              </div>
            )}
            {job.params && Object.keys(job.params).length > 0 && (
              <div className="mt-2 text-xs text-slate-400">
                Params: <span className="text-slate-600 font-mono">{JSON.stringify(job.params)}</span>
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
  const totalPages = Math.ceil(total / 30);

  return (
    <AdministrationLayout
      title="Background Jobs & Automation Center"
      subtitle="Visibility into all background processing, retry and cancel controls"
      actions={
        <Button variant="ghost" size="icon" onClick={refetchAll} aria-label="Refresh">
          <RefreshCw size={14} className={(sLoading || jLoading) ? "animate-spin" : ""} />
        </Button>
      }
    >

      {/* Stats */}
      <StatGrid cols={7}>
        <StatCard label="Total" value={s.total ?? 0} />
        <StatCard label="Running" value={s.running ?? 0} icon={<Play style={{ color: INFO }} />} />
        <StatCard label="Pending" value={s.pending ?? 0} icon={<Pause style={{ color: AMBER }} />} />
        <StatCard label="Completed" value={s.completed ?? 0} icon={<RotateCcw style={{ color: EMERALD }} />} />
        <StatCard label="Failed" value={s.failed ?? 0} icon={<X style={{ color: CRIMSON }} />} />
        <StatCard label="Last 24h" value={s.recent_24h ?? 0} />
        <StatCard label="Success Rate" value={`${s.success_rate_pct ?? 0}%`} />
      </StatGrid>

      {/* By kind */}
      {(s.by_kind || []).length > 0 && (
        <Card padding="lg">
          <div className="text-xs text-slate-500 font-medium mb-3">By Kind</div>
          <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-5 gap-2">
            {s.by_kind.map(k => (
              <div key={k.kind} className="flex items-center justify-between gap-2 text-xs">
                <span className="text-slate-600 font-mono truncate">{k.kind}</span>
                <span className="text-slate-800">{k.count}</span>
                {k.failed > 0 && <span style={{ color: CRIMSON }}>({k.failed} failed)</span>}
              </div>
            ))}
          </div>
        </Card>
      )}

      {/* Trigger job */}
      <Card padding="lg">
        <div className="text-xs text-slate-500 font-medium mb-3">Trigger Background Job</div>
        <div className="flex gap-2 items-center">
          <FormSelect value={triggerKind} onChange={e => setTriggerKind(e.target.value)} wrapperClassName="flex-1 max-w-xs">
            {JOB_TYPES.map(t => <option key={t} value={t}>{t}</option>)}
          </FormSelect>
          <Button variant="primary" size="md" onClick={trigger} loading={triggering}>
            <Play size={11} /> {triggering ? "Enqueuing..." : "Trigger Now"}
          </Button>
          {triggerMsg && <span className="text-xs text-slate-500">{triggerMsg}</span>}
        </div>
      </Card>

      {/* Filters */}
      <div className="flex gap-2 flex-wrap items-center">
        <FormSelect value={status} onChange={e => { setStatus(e.target.value); setPage(1); }} wrapperClassName="w-40">
          <option value="">All statuses</option>
          {["pending","running","completed","failed","paused","cancelled"].map(s => <option key={s} value={s}>{s}</option>)}
        </FormSelect>
        <FormSelect value={kind} onChange={e => { setKind(e.target.value); setPage(1); }} wrapperClassName="w-52">
          <option value="">All kinds</option>
          {JOB_TYPES.map(t => <option key={t} value={t}>{t}</option>)}
        </FormSelect>
        <span className="text-xs text-slate-400">{total} jobs</span>
      </div>

      {/* Jobs table — kept as a raw <table> (not ds/DataTable): rows expand
          in-place to show a job-logs detail row and carry per-row action
          buttons, which DataTable's per-cell `render` API can't express (it
          renders exactly one <tr> per row, no inserted detail row). */}
      <div style={{ border: `1px solid ${BRD}`, borderRadius: 6, overflow: "hidden", background: "white" }}>
        <div className="overflow-x-auto">
          <table className="w-full text-xs text-slate-600">
            <thead className="text-slate-400 border-b border-slate-100 bg-slate-50">
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
              {jLoading && <tr><td colSpan={7} className="px-3 py-8 text-center text-slate-400">Loading...</td></tr>}
              {!jLoading && items.map(j => <JobRow key={j.id} job={j} onRefresh={refetchAll} />)}
              {!jLoading && items.length === 0 && (
                <tr><td colSpan={7} className="px-3 py-8 text-center text-slate-400">No jobs found</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Pagination */}
      {total > 30 && (
        <Pagination page={page} totalPages={totalPages} onPage={setPage} />
      )}
    </AdministrationLayout>
  );
}
