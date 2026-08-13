import React, { useState, useCallback, useEffect } from "react";
import { RefreshCw, MessageSquare, ChevronDown, ChevronRight, Download } from "lucide-react";
import api from "@/lib/api";
import { NAVY } from "@/lib/tokens";
import { AdministrationLayout } from "@/layouts";
import {
  Card, Button, Input, FormSelect, Badge, StatCard, StatGrid, Pagination,
} from "@/components/ds";

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

const PRIORITY_BADGE = {
  critical: "danger",
  high:     "warning",
  medium:   "warning",
  low:      "neutral",
};
const STATUS_BADGE = {
  open:     "danger",
  assigned: "warning",
  resolved: "success",
  closed:   "neutral",
};

// NOTE: this table uses an inline expand/collapse detail row per ticket
// (description, assign/resolve/escalate actions). Like AdminReleases.jsx and
// AdminSubscriptions.jsx, ds/DataTable's column+render API renders exactly
// one <tr> per row with no expandable-detail-row concept, so the table
// markup is left hand-rolled here (re-themed to light + Badge for pills)
// instead of converted to DataTable.
function TicketRow({ ticket, onRefresh }) {
  const [expanded, setExpanded] = useState(false);
  const [assignTo, setAssignTo] = useState(ticket.assigned_to || "");
  const [resolution, setResolution] = useState("");
  const [saving, setSaving] = useState(false);

  const patch = async (updates) => {
    setSaving(true);
    try { await api.patch(`/admin/x/support/tickets/${ticket.id}`, updates); onRefresh(); }
    catch (e) { console.error(e); }
    finally { setSaving(false); }
  };

  return (
    <>
      <tr className="border-t border-slate-100 hover:bg-slate-50 cursor-pointer" onClick={() => setExpanded(v => !v)}>
        <td className="px-3 py-2">
          {expanded ? <ChevronDown size={12} className="text-slate-400" /> : <ChevronRight size={12} className="text-slate-400" />}
        </td>
        <td className="px-3 py-2 max-w-[200px] truncate text-slate-800 text-xs">{ticket.title}</td>
        <td className="px-3 py-2 text-slate-500 text-xs">{ticket.kind}</td>
        <td className="px-3 py-2">
          <Badge variant={PRIORITY_BADGE[ticket.priority] || "neutral"} size="sm">
            {(ticket.priority || "").toUpperCase()}
          </Badge>
        </td>
        <td className="px-3 py-2">
          <Badge variant={STATUS_BADGE[ticket.status] || "neutral"} size="sm">{ticket.status}</Badge>
        </td>
        <td className="px-3 py-2 text-xs text-slate-500">{ticket.assigned_to || "Unassigned"}</td>
        <td className="px-3 py-2 text-xs text-slate-400">{(ticket.created_at || "").slice(0, 10)}</td>
      </tr>
      {expanded && (
        <tr className="border-t border-slate-100 bg-slate-50">
          <td colSpan={7} className="px-4 py-4">
            <div className="space-y-4">
              <div>
                <div className="text-[10px] text-slate-500 mb-1">Description</div>
                <div className="text-xs text-slate-600 whitespace-pre-wrap">{ticket.description}</div>
              </div>
              {ticket.email && <div className="text-xs text-slate-500">Contact: <span className="text-blue-600">{ticket.email}</span></div>}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                <div>
                  <label className="text-[10px] text-slate-500 block mb-1">Assign to</label>
                  <div className="flex gap-1.5 items-start">
                    <Input
                      value={assignTo}
                      onChange={e => setAssignTo(e.target.value)}
                      placeholder="admin@email.com"
                      size="sm"
                      wrapperClassName="flex-1 !mb-0"
                    />
                    <Button variant="primary" size="sm" onClick={() => patch({ assigned_to: assignTo, status: "assigned" })} disabled={saving || !assignTo}>
                      Assign
                    </Button>
                  </div>
                </div>
                <div>
                  <label className="text-[10px] text-slate-500 block mb-1">Resolution</label>
                  <div className="flex gap-1.5 items-start">
                    <Input
                      value={resolution}
                      onChange={e => setResolution(e.target.value)}
                      placeholder="Describe resolution..."
                      size="sm"
                      wrapperClassName="flex-1 !mb-0"
                    />
                    <Button variant="primary" size="sm" className="!bg-emerald-700 hover:!bg-emerald-600" onClick={() => patch({ status: "resolved", resolution })} disabled={saving}>
                      Resolve
                    </Button>
                  </div>
                </div>
                <div className="flex items-end gap-2">
                  <Button variant="outline" size="sm" className="!border-red-300 !text-red-600 hover:!bg-red-50" onClick={() => patch({ priority: "critical" })} disabled={saving}>
                    Escalate Critical
                  </Button>
                  <Button variant="ghost" size="sm" onClick={() => patch({ status: "closed" })} disabled={saving}>
                    Close
                  </Button>
                </div>
              </div>
              {ticket.resolution && (
                <div className="text-xs text-emerald-700 bg-emerald-50 border border-emerald-200 p-2 rounded-md">
                  Resolution: {ticket.resolution}
                </div>
              )}
            </div>
          </td>
        </tr>
      )}
    </>
  );
}

export default function AdminSupportCenter() {
  const [status, setStatus] = useState("");
  const [priority, setPriority] = useState("");
  const [days, setDays] = useState(30);
  const [page, setPage] = useState(1);

  const { data: stats, loading: sL, refetch: refStats } = useX("support/stats", { days });
  const { data: tickets, loading: tL, refetch: refTickets } = useX("support/tickets", { status, priority, page, limit: 30 });
  const refetchAll = () => { refStats(); refTickets(); };

  const s = stats || {};
  const items = tickets?.items || [];
  const total = tickets?.total || 0;

  const exportCSV = () => { window.open("/api/admin/x/support/export", "_blank"); };

  return (
    <AdministrationLayout
      title="Support & Customer Success Center"
      subtitle="Ticket management, assignment, escalation, and SLA tracking"
      actions={
        <div className="flex gap-2">
          <Button variant="hero" size="sm" onClick={exportCSV}>
            <Download size={12} /> Export CSV
          </Button>
          <FormSelect value={days} onChange={e => setDays(Number(e.target.value))} size="sm" wrapperClassName="!mb-0">
            {[7, 14, 30, 90].map(d => <option key={d} value={d}>Last {d}d</option>)}
          </FormSelect>
          <Button variant="hero" size="icon" onClick={refetchAll} aria-label="Refresh">
            <RefreshCw size={14} className={(sL || tL) ? "animate-spin" : ""} />
          </Button>
        </div>
      }
    >
      <div className="flex flex-col gap-6">
        {/* Stats */}
        <StatGrid cols={7}>
          <StatCard label="Total" value={s.total ?? 0} />
          <StatCard label="Open" value={s.open ?? 0} />
          <StatCard label="Resolved" value={s.resolved ?? 0} />
          <StatCard label="New (period)" value={s.new_period ?? 0} />
          <StatCard label="Resolution %" value={`${s.resolution_rate_pct ?? 0}%`} />
          <StatCard label="Avg Resolve" value={`${s.avg_resolution_hours ?? 0}h`} />
          <StatCard label="Critical Open" value={s.by_priority?.critical ?? 0} />
        </StatGrid>

        {/* By kind and priority */}
        {(s.by_kind || s.by_priority) && (
          <div className="grid grid-cols-2 gap-4">
            {[
              { title: "By Kind", data: s.by_kind || {} },
              { title: "By Priority", data: s.by_priority || {} },
            ].map(({ title, data: d }) => (
              <Card key={title} padding="md">
                <div className="text-xs text-slate-500 font-medium mb-2">{title}</div>
                <div className="grid grid-cols-2 gap-2">
                  {Object.entries(d).map(([k, v]) => (
                    <div key={k} className="flex items-center justify-between text-xs">
                      <span className="text-slate-500 capitalize">{k}</span>
                      <span className="text-slate-900 font-medium">{v}</span>
                    </div>
                  ))}
                </div>
              </Card>
            ))}
          </div>
        )}

        {/* Filters */}
        <div className="flex gap-2 flex-wrap items-center">
          <FormSelect value={status} onChange={e => { setStatus(e.target.value); setPage(1); }} size="sm" wrapperClassName="!mb-0">
            <option value="">All statuses</option>
            {["open","assigned","resolved","closed"].map(s => <option key={s} value={s}>{s}</option>)}
          </FormSelect>
          <FormSelect value={priority} onChange={e => { setPriority(e.target.value); setPage(1); }} size="sm" wrapperClassName="!mb-0">
            <option value="">All priorities</option>
            {["critical","high","medium","low"].map(p => <option key={p} value={p}>{p}</option>)}
          </FormSelect>
          <span className="text-xs text-slate-500">{total} tickets</span>
        </div>

        {/* Tickets table */}
        <Card padding="none" className="overflow-x-auto">
          <table className="w-full text-xs text-slate-600">
            <thead className="text-slate-500 border-b border-slate-200 bg-slate-50">
              <tr>
                <th className="px-3 py-2 w-6" />
                <th className="text-left px-3 py-2 font-medium">Title</th>
                <th className="text-left px-3 py-2 font-medium">Kind</th>
                <th className="text-left px-3 py-2 font-medium">Priority</th>
                <th className="text-left px-3 py-2 font-medium">Status</th>
                <th className="text-left px-3 py-2 font-medium">Assigned</th>
                <th className="text-left px-3 py-2 font-medium">Created</th>
              </tr>
            </thead>
            <tbody>
              {tL && <tr><td colSpan={7} className="px-3 py-8 text-center text-slate-400">Loading...</td></tr>}
              {!tL && items.map(t => <TicketRow key={t.id} ticket={t} onRefresh={refetchAll} />)}
              {!tL && items.length === 0 && (
                <tr><td colSpan={7} className="px-3 py-8 text-center text-slate-400">No tickets found</td></tr>
              )}
            </tbody>
          </table>
        </Card>

        {total > 30 && (
          <Pagination page={page} totalPages={Math.ceil(total / 30)} onPage={(p) => setPage(p)} />
        )}
      </div>
    </AdministrationLayout>
  );
}
