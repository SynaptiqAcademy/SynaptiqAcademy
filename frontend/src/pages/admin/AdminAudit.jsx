/* eslint-disable */
import React, { useState, useEffect, useCallback } from "react";
import { ShieldCheck, ChevronLeft, ChevronRight, ChevronDown, ChevronUp } from "lucide-react";
import api from "@/lib/api";
import { NAVY } from "@/lib/tokens";
import { AdministrationLayout } from "@/layouts";

const LIMIT = 50;

function ActionBadge({ action }) {
  if (!action) return null;
  const prefix = action.split(".")[0];
  const styles = {
    auth: "bg-blue-50 text-blue-700",
    admin: "bg-rose-50 text-rose-700",
    user: "bg-green-50 text-green-700",
  };
  return (
    <span className={`inline-block px-2 py-0.5 text-xs font-mono font-medium ${styles[prefix] || "bg-slate-100 text-slate-700"}`}>
      {action}
    </span>
  );
}

function Skeleton() {
  return (
    <div className="space-y-2 p-4">
      {[...Array(8)].map((_, i) => <div key={i} className="h-10 animate-pulse bg-gray-200" />)}
    </div>
  );
}

export default function AdminAudit() {
  const [items, setItems] = useState([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [filterAction, setFilterAction] = useState("");
  const [filterFrom, setFilterFrom] = useState("");
  const [filterTo, setFilterTo] = useState("");
  const [expandedRows, setExpandedRows] = useState(new Set());

  const fetchAudit = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const params = new URLSearchParams({ page, limit: LIMIT });
      if (filterAction) params.set("action", filterAction);
      if (filterFrom) params.set("from_date", filterFrom);
      if (filterTo) params.set("to_date", filterTo);
      const r = await api.get(`/admin/audit?${params}`);
      setItems(r.data.items || []);
      setTotal(r.data.total || 0);
    } catch (e) {
      setError(e.response?.data?.detail || "Failed to load audit log");
    } finally {
      setLoading(false);
    }
  }, [page, filterAction, filterFrom, filterTo]);

  useEffect(() => { fetchAudit(); }, [fetchAudit]);

  const toggleRow = (i) => setExpandedRows((prev) => {
    const next = new Set(prev);
    next.has(i) ? next.delete(i) : next.add(i);
    return next;
  });

  const totalPages = Math.ceil(total / LIMIT);
  const fmt = (d) => d ? new Date(d).toLocaleDateString("en-GB", { day: "2-digit", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit" }) : "—";

  return (
    <AdministrationLayout title="Audit Center" subtitle="Complete record of all platform events">
      {/* Filters */}
      <div className="flex gap-3 mb-4 flex-wrap">
        <input
          type="text"
          placeholder="Filter by action (e.g. auth.login)"
          value={filterAction}
          onChange={(e) => { setFilterAction(e.target.value); setPage(1); }}
          className="px-3 py-2 text-sm border border-slate-300 bg-white focus:outline-none focus:ring-1 focus:ring-[#0F2847] w-64"
        />
        <input type="date" value={filterFrom} onChange={(e) => { setFilterFrom(e.target.value); setPage(1); }}
          className="px-3 py-2 text-sm border border-slate-300 bg-white focus:outline-none focus:ring-1 focus:ring-[#0F2847]" />
        <input type="date" value={filterTo} onChange={(e) => { setFilterTo(e.target.value); setPage(1); }}
          className="px-3 py-2 text-sm border border-slate-300 bg-white focus:outline-none focus:ring-1 focus:ring-[#0F2847]" />
        {(filterAction || filterFrom || filterTo) && (
          <button onClick={() => { setFilterAction(""); setFilterFrom(""); setFilterTo(""); setPage(1); }}
            className="px-3 py-2 text-xs text-slate-600 border border-slate-300 hover:bg-slate-50">
            Clear filters
          </button>
        )}
      </div>

      {error && <div className="mb-4 bg-red-50 border border-red-200 text-red-800 px-4 py-2 text-sm">{error}</div>}

      {!loading && (
        <p className="text-xs text-slate-500 mb-3">{total > 0 ? `${total.toLocaleString()} events total` : "No events found"}</p>
      )}

      <div className="bg-white border border-slate-200 overflow-hidden">
        {loading ? (
          <Skeleton />
        ) : items.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-16 text-slate-400">
            <ShieldCheck size={36} className="mb-3 opacity-40" />
            <p className="text-sm">No audit events found</p>
          </div>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-200 bg-slate-50">
                <th className="text-left px-4 py-3 text-xs font-semibold uppercase tracking-widest text-slate-500">Time</th>
                <th className="text-left px-4 py-3 text-xs font-semibold uppercase tracking-widest text-slate-500">Action</th>
                <th className="text-left px-4 py-3 text-xs font-semibold uppercase tracking-widest text-slate-500">Actor</th>
                <th className="text-left px-4 py-3 text-xs font-semibold uppercase tracking-widest text-slate-500">Target</th>
                <th className="text-left px-4 py-3 text-xs font-semibold uppercase tracking-widest text-slate-500">IP</th>
                <th className="px-4 py-3" />
              </tr>
            </thead>
            <tbody>
              {items.map((ev, i) => (
                <React.Fragment key={i}>
                  <tr className="border-b border-slate-100 hover:bg-slate-50">
                    <td className="px-4 py-2.5 text-xs text-slate-500 whitespace-nowrap">{fmt(ev.created_at)}</td>
                    <td className="px-4 py-2.5"><ActionBadge action={ev.action} /></td>
                    <td className="px-4 py-2.5 text-xs text-slate-600">{ev.actor_email || ev.actor_id || "—"}</td>
                    <td className="px-4 py-2.5 text-xs text-slate-600">{ev.target_email || ev.target_id || "—"}</td>
                    <td className="px-4 py-2.5 text-xs text-slate-400">{ev.ip || "—"}</td>
                    <td className="px-4 py-2.5">
                      {ev.extra && Object.keys(ev.extra).length > 0 && (
                        <button onClick={() => toggleRow(i)} className="text-slate-400 hover:text-slate-700">
                          {expandedRows.has(i) ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
                        </button>
                      )}
                    </td>
                  </tr>
                  {expandedRows.has(i) && (
                    <tr className="border-b border-slate-100 bg-slate-50">
                      <td colSpan={6} className="px-4 py-2">
                        <pre className="text-xs text-slate-700 font-mono whitespace-pre-wrap bg-slate-100 p-3 overflow-x-auto">
                          {JSON.stringify(ev.extra, null, 2)}
                        </pre>
                      </td>
                    </tr>
                  )}
                </React.Fragment>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {totalPages > 1 && (
        <div className="flex items-center justify-between mt-4">
          <button onClick={() => setPage((p) => Math.max(1, p - 1))} disabled={page === 1}
            className="flex items-center gap-1 text-sm text-slate-600 hover:text-slate-900 disabled:opacity-40">
            <ChevronLeft size={14} /> Previous
          </button>
          <span className="text-xs text-slate-500">Page {page} of {totalPages}</span>
          <button onClick={() => setPage((p) => Math.min(totalPages, p + 1))} disabled={page === totalPages}
            className="flex items-center gap-1 text-sm text-slate-600 hover:text-slate-900 disabled:opacity-40">
            Next <ChevronRight size={14} />
          </button>
        </div>
      )}
    </AdministrationLayout>
  );
}
