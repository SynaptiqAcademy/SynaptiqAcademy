/* eslint-disable */
import React, { useState, useEffect, useCallback } from "react";
import { AlertTriangle, AlertCircle, CheckCircle, RefreshCw, Download, X } from "lucide-react";
import api from "@/lib/api";
import { AdministrationLayout } from "@/layouts";
import { Button, Input, FormSelect, Badge, StatCard, StatGrid } from "@/components/ds";

function useAOS(path, params = {}) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const query = new URLSearchParams(params).toString();
  const fetch = useCallback(() => {
    setLoading(true);
    api.get(`/admin/aos/${path}${query ? "?" + query : ""}`)
      .then((r) => setData(r.data))
      .catch(() => setData(null))
      .finally(() => setLoading(false));
  }, [path, query]);
  useEffect(() => { fetch(); }, [fetch]);
  return { data, loading, refetch: fetch };
}

const SEVERITY_VARIANT = {
  critical: "danger",
  high:     "warning",
  medium:   "warning",
  low:      "info",
};

const SEVERITY_ICON_COLOR = {
  critical: "text-red-600",
  high:     "text-orange-600",
  medium:   "text-amber-600",
  low:      "text-blue-600",
};

const SEVERITY_ICONS = {
  critical: AlertCircle,
  high:     AlertTriangle,
  medium:   AlertTriangle,
  low:      AlertCircle,
};

function SeverityBadge({ severity }) {
  return <Badge size="sm" variant={SEVERITY_VARIANT[severity] || "neutral"}>{severity}</Badge>;
}

function ErrorRow({ err, onUpdate }) {
  const [expanded, setExpanded] = useState(false);
  const [resolving, setResolving] = useState(false);
  const [owner, setOwner] = useState(err.owner || "");
  const [note, setNote] = useState("");

  const resolve = async () => {
    setResolving(true);
    try {
      await api.patch(`/admin/aos/errors/${err.id}`, {
        resolved: true,
        owner:    owner || undefined,
        note:     note || undefined,
      });
      onUpdate();
    } catch (e) {
      console.error(e);
    } finally {
      setResolving(false);
    }
  };

  const Icon = SEVERITY_ICONS[err.severity] || AlertTriangle;

  return (
    <>
      <tr
        className="border-t border-slate-100 hover:bg-slate-50 cursor-pointer"
        onClick={() => setExpanded((v) => !v)}
      >
        <td className="px-3 py-2">
          <Icon size={12} className={SEVERITY_ICON_COLOR[err.severity] || "text-blue-600"} />
        </td>
        <td className="px-3 py-2"><SeverityBadge severity={err.severity} /></td>
        <td className="px-3 py-2 text-slate-400 text-[10px]">{err.category}</td>
        <td className="px-3 py-2 text-slate-800 max-w-xs truncate">{err.message}</td>
        <td className="px-3 py-2 text-slate-400 text-[10px]">{err.endpoint || "—"}</td>
        <td className="px-3 py-2 text-slate-500">{err.frequency}</td>
        <td className="px-3 py-2 text-slate-400 text-[10px]">{(err.last_seen || "").slice(0, 16)}</td>
        <td className="px-3 py-2">
          {err.resolved ? (
            <CheckCircle size={12} className="text-emerald-600" />
          ) : (
            <X size={12} className="text-red-600" />
          )}
        </td>
      </tr>
      {expanded && (
        <tr className="border-t border-slate-100 bg-slate-50">
          <td colSpan={8} className="px-4 py-4">
            <div className="space-y-3">
              {err.stack_trace && (
                <div>
                  <div className="text-[10px] text-slate-400 mb-1">Stack Trace</div>
                  <pre className="text-[10px] text-slate-600 bg-white p-3 overflow-x-auto max-h-48 border border-slate-200">
                    {err.stack_trace}
                  </pre>
                </div>
              )}
              <div className="flex items-end gap-3 flex-wrap">
                <Input
                  type="text"
                  label="Assign to"
                  value={owner}
                  onChange={(e) => setOwner(e.target.value)}
                  placeholder="email or name"
                  size="sm"
                  wrapperClassName="w-40"
                />
                <Input
                  type="text"
                  label="Remediation Note"
                  value={note}
                  onChange={(e) => setNote(e.target.value)}
                  placeholder="What was fixed?"
                  size="sm"
                  wrapperClassName="w-64"
                />
                {!err.resolved && (
                  <Button variant="primary" size="sm" onClick={resolve} loading={resolving} className="bg-emerald-600 hover:bg-emerald-700">
                    <CheckCircle size={11} />
                    {resolving ? "Resolving..." : "Mark Resolved"}
                  </Button>
                )}
                <div className="text-[10px] text-slate-400">
                  First seen: {(err.first_seen || "").slice(0, 16)} · Browser: {err.browser || "—"}
                </div>
              </div>
            </div>
          </td>
        </tr>
      )}
    </>
  );
}

export default function AdminErrorCenter() {
  const [severity, setSeverity] = useState("");
  const [category, setCategory] = useState("");
  const [resolved, setResolved] = useState("");
  const [page, setPage] = useState(1);

  const params = { page, limit: 50 };
  if (severity) params.severity = severity;
  if (category) params.category = category;
  if (resolved !== "") params.resolved = resolved === "true";

  const { data, loading, refetch } = useAOS("errors", params);
  const { data: stats, refetch: refetchStats } = useAOS("errors/stats");

  const items = data?.items || [];
  const total = data?.total || 0;

  const refresh = () => { refetch(); refetchStats(); };

  return (
    <AdministrationLayout
      title="Error & Incident Center"
      subtitle="Detect, triage, and resolve platform errors"
      actions={
        <div className="flex gap-2">
          <Button variant="ghost" size="sm" onClick={() => window.open("/api/admin/aos/errors/export", "_blank")}>
            <Download size={12} />
            Export CSV
          </Button>
          <Button variant="ghost" size="icon" onClick={refresh} aria-label="Refresh">
            <RefreshCw size={14} className={loading ? "animate-spin" : ""} />
          </Button>
        </div>
      }
    >

      {/* Stats */}
      {stats && (
        <StatGrid cols={4}>
          <StatCard label="Unresolved" value={stats.unresolved} />
          <StatCard label="Critical (open)" value={stats.critical} className={stats.critical > 0 ? "border-red-200" : ""} />
          <StatCard label="New (24h)" value={stats.new_24h} />
          <div className="bg-white border border-slate-200 rounded-md p-3 space-y-1">
            {(stats.by_severity || []).slice(0, 3).map((s) => (
              <div key={s.severity} className="flex justify-between text-xs">
                <span className="text-slate-500">{s.severity}</span>
                <span className="text-slate-800 font-medium">{s.count}</span>
              </div>
            ))}
          </div>
        </StatGrid>
      )}

      {/* Category breakdown */}
      {stats?.by_category && (
        <div className="bg-white border border-slate-200 p-4">
          <div className="text-xs font-semibold text-slate-500 mb-2">By Category</div>
          <div className="flex flex-wrap gap-2">
            {stats.by_category.map((c) => (
              <button
                key={c.category}
                onClick={() => setCategory(category === c.category ? "" : c.category)}
                className={`text-xs px-2 py-1 border transition-colors ${
                  category === c.category
                    ? "bg-navy-700 border-navy-700 text-white"
                    : "bg-slate-50 border-slate-200 text-slate-600 hover:text-slate-900"
                }`}
              >
                {c.category}: {c.count}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Filters */}
      <div className="flex items-center gap-2 flex-wrap">
        <FormSelect
          value={severity}
          onChange={(e) => { setSeverity(e.target.value); setPage(1); }}
          wrapperClassName="w-40"
        >
          <option value="">All Severities</option>
          <option value="critical">Critical</option>
          <option value="high">High</option>
          <option value="medium">Medium</option>
          <option value="low">Low</option>
        </FormSelect>
        <FormSelect
          value={category}
          onChange={(e) => { setCategory(e.target.value); setPage(1); }}
          wrapperClassName="w-40"
        >
          <option value="">All Categories</option>
          <option value="frontend">Frontend</option>
          <option value="backend">Backend</option>
          <option value="api">API</option>
          <option value="database">Database</option>
          <option value="payment">Payment</option>
          <option value="auth">Auth</option>
          <option value="email">Email</option>
        </FormSelect>
        <FormSelect
          value={resolved}
          onChange={(e) => { setResolved(e.target.value); setPage(1); }}
          wrapperClassName="w-40"
        >
          <option value="">All Statuses</option>
          <option value="false">Unresolved</option>
          <option value="true">Resolved</option>
        </FormSelect>
        <span className="text-xs text-slate-400 ml-2">{total} errors</span>
      </div>

      {/* Error table — kept as a raw <table> (not ds/DataTable): rows expand
          in-place to show a stack-trace/assign/resolve detail row, which
          DataTable's per-cell `render` API can't express (it renders exactly
          one <tr> per row, no inserted detail row). */}
      <div className="bg-white border border-slate-200 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-xs text-slate-600">
            <thead className="text-slate-400 border-b border-slate-100 bg-slate-50">
              <tr>
                <th className="px-3 py-2 w-6" />
                <th className="text-left px-3 py-2 font-medium">Severity</th>
                <th className="text-left px-3 py-2 font-medium">Category</th>
                <th className="text-left px-3 py-2 font-medium">Message</th>
                <th className="text-left px-3 py-2 font-medium">Endpoint</th>
                <th className="text-left px-3 py-2 font-medium">Frequency</th>
                <th className="text-left px-3 py-2 font-medium">Last Seen</th>
                <th className="text-left px-3 py-2 font-medium">Resolved</th>
              </tr>
            </thead>
            <tbody>
              {loading && (
                <tr><td colSpan={8} className="px-3 py-8 text-center text-slate-400">Loading...</td></tr>
              )}
              {!loading && items.map((err) => (
                <ErrorRow key={err.id} err={err} onUpdate={refresh} />
              ))}
              {!loading && items.length === 0 && (
                <tr>
                  <td colSpan={8} className="px-3 py-8 text-center text-slate-400">
                    <CheckCircle size={24} className="text-emerald-600 mx-auto mb-2" />
                    No errors matching current filters
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
        <div className="flex items-center justify-between px-3 py-2 border-t border-slate-100 bg-slate-50">
          <span className="text-xs text-slate-400">{total} total · Click any row to expand</span>
          <div className="flex gap-2">
            <Button variant="ghost" size="sm" disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>Prev</Button>
            <span className="text-xs text-slate-500 px-2 py-1">Page {page}</span>
            <Button variant="ghost" size="sm" disabled={items.length < 50} onClick={() => setPage((p) => p + 1)}>Next</Button>
          </div>
        </div>
      </div>
    </AdministrationLayout>
  );
}
