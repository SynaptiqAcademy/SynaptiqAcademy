import React, { useState, useCallback, useEffect } from "react";
import { RefreshCw, MessageSquare, ChevronDown, ChevronRight, Download } from "lucide-react";
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

const PRIORITY_COLOR = {
  critical: "text-red-400 border-red-700",
  high:     "text-orange-400 border-orange-700",
  medium:   "text-yellow-400 border-yellow-700",
  low:      "text-slate-400 border-slate-600",
};
const STATUS_COLOR = {
  open:     "text-red-400",
  assigned: "text-yellow-400",
  resolved: "text-green-400",
  closed:   "text-slate-500",
};

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
      <tr className="border-t border-[#1a3050] hover:bg-[#1a3050]/30 cursor-pointer" onClick={() => setExpanded(v => !v)}>
        <td className="px-3 py-2">
          {expanded ? <ChevronDown size={12} className="text-slate-400" /> : <ChevronRight size={12} className="text-slate-400" />}
        </td>
        <td className="px-3 py-2 max-w-[200px] truncate text-white text-xs">{ticket.title}</td>
        <td className="px-3 py-2 text-slate-400 text-xs">{ticket.kind}</td>
        <td className="px-3 py-2">
          <span className={`text-[10px] px-1.5 py-0.5 border ${PRIORITY_COLOR[ticket.priority] || "text-slate-400 border-slate-600"}`}>
            {(ticket.priority || "").toUpperCase()}
          </span>
        </td>
        <td className="px-3 py-2">
          <span className={`text-xs ${STATUS_COLOR[ticket.status] || "text-slate-400"}`}>{ticket.status}</span>
        </td>
        <td className="px-3 py-2 text-xs text-slate-400">{ticket.assigned_to || "Unassigned"}</td>
        <td className="px-3 py-2 text-xs text-slate-500">{(ticket.created_at || "").slice(0, 10)}</td>
      </tr>
      {expanded && (
        <tr className="border-t border-[#1a3050] bg-[#080f1f]">
          <td colSpan={7} className="px-4 py-4">
            <div className="space-y-4">
              <div>
                <div className="text-[10px] text-slate-500 mb-1">Description</div>
                <div className="text-xs text-slate-300 whitespace-pre-wrap">{ticket.description}</div>
              </div>
              {ticket.email && <div className="text-xs text-slate-400">Contact: <span className="text-blue-400">{ticket.email}</span></div>}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                <div>
                  <label className="text-[10px] text-slate-500 block mb-1">Assign to</label>
                  <div className="flex gap-1.5">
                    <input value={assignTo} onChange={e => setAssignTo(e.target.value)}
                      placeholder="admin@email.com"
                      className="flex-1 text-xs bg-[#0B1C35] border border-[#1a3050] text-slate-300 px-2 py-1" />
                    <button onClick={() => patch({ assigned_to: assignTo, status: "assigned" })} disabled={saving || !assignTo}
                      className="text-[10px] text-white bg-blue-700 hover:bg-blue-600 px-2 disabled:opacity-50">Assign</button>
                  </div>
                </div>
                <div>
                  <label className="text-[10px] text-slate-500 block mb-1">Resolution</label>
                  <div className="flex gap-1.5">
                    <input value={resolution} onChange={e => setResolution(e.target.value)}
                      placeholder="Describe resolution..."
                      className="flex-1 text-xs bg-[#0B1C35] border border-[#1a3050] text-slate-300 px-2 py-1" />
                    <button onClick={() => patch({ status: "resolved", resolution })} disabled={saving}
                      className="text-[10px] text-white bg-green-700 hover:bg-green-600 px-2 disabled:opacity-50">Resolve</button>
                  </div>
                </div>
                <div className="flex items-end gap-2">
                  <button onClick={() => patch({ priority: "critical" })} disabled={saving}
                    className="text-[10px] border border-red-700 text-red-400 hover:bg-red-900/20 px-2 py-1 disabled:opacity-50">
                    Escalate Critical
                  </button>
                  <button onClick={() => patch({ status: "closed" })} disabled={saving}
                    className="text-[10px] border border-slate-600 text-slate-400 hover:text-white px-2 py-1 disabled:opacity-50">
                    Close
                  </button>
                </div>
              </div>
              {ticket.resolution && (
                <div className="text-xs text-green-300 bg-green-900/20 border border-green-700/40 p-2">
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
          <button onClick={exportCSV} className="flex items-center gap-1.5 text-xs bg-[#0F2847] border border-[#1a3050] text-slate-400 hover:text-white px-3 py-1.5">
            <Download size={12} /> Export CSV
          </button>
          <select value={days} onChange={e => setDays(Number(e.target.value))}
            className="text-xs bg-[#0F2847] border border-[#1a3050] text-slate-300 px-2 py-1.5">
            {[7, 14, 30, 90].map(d => <option key={d} value={d}>Last {d}d</option>)}
          </select>
          <button onClick={refetchAll} className="p-1.5 bg-[#0F2847] border border-[#1a3050] text-slate-400 hover:text-white">
            <RefreshCw size={14} className={(sL || tL) ? "animate-spin" : ""} />
          </button>
        </div>
      }
    >

      {/* Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-7 gap-3">
        {[
          { label: "Total", value: s.total, color: "text-white" },
          { label: "Open", value: s.open, color: "text-red-400" },
          { label: "Resolved", value: s.resolved, color: "text-green-400" },
          { label: "New (period)", value: s.new_period, color: "text-blue-400" },
          { label: "Resolution %", value: `${s.resolution_rate_pct ?? 0}%`, color: s.resolution_rate_pct >= 70 ? "text-green-400" : "text-yellow-400" },
          { label: "Avg Resolve", value: `${s.avg_resolution_hours ?? 0}h`, color: "text-slate-300" },
          { label: "Critical Open", value: s.by_priority?.critical ?? 0, color: "text-red-400" },
        ].map(({ label, value, color }) => (
          <div key={label} className="bg-[#0F2847] border border-[#1a3050] p-3">
            <div className={`text-xl font-bold ${color}`}>{value ?? 0}</div>
            <div className="text-[10px] text-slate-500">{label}</div>
          </div>
        ))}
      </div>

      {/* By kind and priority */}
      {(s.by_kind || s.by_priority) && (
        <div className="grid grid-cols-2 gap-4">
          {[
            { title: "By Kind", data: s.by_kind || {} },
            { title: "By Priority", data: s.by_priority || {} },
          ].map(({ title, data: d }) => (
            <div key={title} className="bg-[#0F2847] border border-[#1a3050] p-4">
              <div className="text-xs text-slate-500 font-medium mb-2">{title}</div>
              <div className="grid grid-cols-2 gap-2">
                {Object.entries(d).map(([k, v]) => (
                  <div key={k} className="flex items-center justify-between text-xs">
                    <span className="text-slate-400 capitalize">{k}</span>
                    <span className="text-white font-medium">{v}</span>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Filters */}
      <div className="flex gap-2 flex-wrap">
        <select value={status} onChange={e => { setStatus(e.target.value); setPage(1); }}
          className="text-xs bg-[#0F2847] border border-[#1a3050] text-slate-300 px-2 py-1.5">
          <option value="">All statuses</option>
          {["open","assigned","resolved","closed"].map(s => <option key={s} value={s}>{s}</option>)}
        </select>
        <select value={priority} onChange={e => { setPriority(e.target.value); setPage(1); }}
          className="text-xs bg-[#0F2847] border border-[#1a3050] text-slate-300 px-2 py-1.5">
          <option value="">All priorities</option>
          {["critical","high","medium","low"].map(p => <option key={p} value={p}>{p}</option>)}
        </select>
        <span className="text-xs text-slate-500 self-center">{total} tickets</span>
      </div>

      {/* Tickets table */}
      <div className="bg-[#0F2847] border border-[#1a3050] overflow-x-auto">
        <table className="w-full text-xs text-slate-300">
          <thead className="text-slate-500 border-b border-[#1a3050]">
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
            {tL && <tr><td colSpan={7} className="px-3 py-8 text-center text-slate-500">Loading...</td></tr>}
            {!tL && items.map(t => <TicketRow key={t.id} ticket={t} onRefresh={refetchAll} />)}
            {!tL && items.length === 0 && (
              <tr><td colSpan={7} className="px-3 py-8 text-center text-slate-500">No tickets found</td></tr>
            )}
          </tbody>
        </table>
      </div>

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
