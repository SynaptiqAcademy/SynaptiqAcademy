/* eslint-disable */
import React, { useState, useEffect, useCallback } from "react";
import { ShieldCheck, ChevronDown, ChevronUp, Clock, BarChart2 } from "lucide-react";
import api from "@/lib/api";
import { NAVY } from "@/lib/tokens";
import { AdministrationLayout } from "@/layouts";
import { Input, Button, Badge, EmptyState, Alert, Pagination, SkeletonTable, Card } from "@/components/ds";

const LIMIT = 50;

const ACTION_BADGE_VARIANT = {
  auth: "info",
  admin: "danger",
  user: "success",
};

function ActionBadge({ action }) {
  if (!action) return null;
  const prefix = action.split(".")[0];
  return (
    <Badge variant={ACTION_BADGE_VARIANT[prefix] || "neutral"} className="font-mono">
      {action}
    </Badge>
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
    <AdministrationLayout
      title="Audit Center"
      subtitle="Complete record of all platform events"
      sidebar={!loading && items.length > 0 ? <AuditSidebar items={items} fmt={fmt} /> : undefined}
    >
      {/* Filters */}
      <div className="flex gap-3 mb-4 flex-wrap items-start">
        <Input
          type="text"
          placeholder="Filter by action (e.g. auth.login)"
          value={filterAction}
          onChange={(e) => { setFilterAction(e.target.value); setPage(1); }}
          wrapperClassName="w-64"
        />
        <Input
          type="date"
          value={filterFrom}
          onChange={(e) => { setFilterFrom(e.target.value); setPage(1); }}
        />
        <Input
          type="date"
          value={filterTo}
          onChange={(e) => { setFilterTo(e.target.value); setPage(1); }}
        />
        {(filterAction || filterFrom || filterTo) && (
          <Button
            variant="outline"
            size="sm"
            onClick={() => { setFilterAction(""); setFilterFrom(""); setFilterTo(""); setPage(1); }}
          >
            Clear filters
          </Button>
        )}
      </div>

      {error && <Alert variant="error" className="mb-4">{error}</Alert>}

      {!loading && (
        <p className="text-xs text-slate-500 mb-3">{total > 0 ? `${total.toLocaleString()} events total` : "No events found"}</p>
      )}

      <div className="bg-white border border-slate-200 overflow-hidden">
        {loading ? (
          <SkeletonTable rows={8} cols={6} />
        ) : items.length === 0 ? (
          <EmptyState icon={<ShieldCheck />} title="No audit events found" />
        ) : (
          /* Kept as a raw <table> (not ds/DataTable): rows expand in-place to show a
             JSON detail row, a feature DataTable's per-cell `render` API has no way
             to express (it renders exactly one <tr> per row, no inserted detail row). */
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
                        <button onClick={() => toggleRow(i)} aria-label={expandedRows.has(i) ? "Collapse details" : "Expand details"} className="text-slate-400 hover:text-slate-700">
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
        <Pagination page={page} totalPages={totalPages} onPage={setPage} className="mt-4" />
      )}
    </AdministrationLayout>
  );
}

// ── Right rail — computed from the events already loaded on this page ─────────
function AuditSidebar({ items, fmt }) {
  const latest = items[0];
  const actionCounts = items.reduce((acc, ev) => {
    const prefix = (ev.action || "other").split(".")[0];
    acc[prefix] = (acc[prefix] || 0) + 1;
    return acc;
  }, {});

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      <Card padding="lg">
        <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 8 }}>
          <Clock size={13} style={{ color: NAVY }} />
          <div style={{ fontSize: 13, fontWeight: 700, color: "#0f172a" }}>Latest Event</div>
        </div>
        <div style={{ fontFamily: "Georgia, serif", fontSize: 14, color: "#0f172a" }}>{latest.action || "—"}</div>
        <p style={{ fontSize: 12, color: "#64748B", margin: "4px 0 0" }}>
          {latest.actor_email || latest.actor_id || "—"} · {fmt(latest.created_at)}
        </p>
      </Card>

      <Card padding="lg">
        <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 8 }}>
          <BarChart2 size={13} style={{ color: NAVY }} />
          <div style={{ fontSize: 13, fontWeight: 700, color: "#0f172a" }}>Action Breakdown</div>
        </div>
        <p style={{ fontSize: 11, color: "#94A3B8", margin: "0 0 8px" }}>Across the {items.length} events currently loaded</p>
        <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
          {Object.entries(actionCounts).map(([prefix, count]) => (
            <div key={prefix} style={{ display: "flex", justifyContent: "space-between", fontSize: 12, color: "#374151" }}>
              <span className="capitalize">{prefix}</span>
              <span>{count}</span>
            </div>
          ))}
        </div>
      </Card>
    </div>
  );
}
