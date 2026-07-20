/* eslint-disable */
import React, { useState, useEffect, useCallback } from "react";
import { AlertTriangle, AlertCircle, CheckCircle, RefreshCw, Download, X } from "lucide-react";
import api from "@/lib/api";
import { NAVY } from "@/lib/tokens";
import { AdministrationLayout } from "@/layouts";

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

const SEVERITY_COLORS = {
  critical: "text-red-400 bg-red-900/30 border-red-700",
  high:     "text-orange-400 bg-orange-900/30 border-orange-700",
  medium:   "text-yellow-400 bg-yellow-900/30 border-yellow-700",
  low:      "text-blue-400 bg-blue-900/30 border-blue-700",
};

const SEVERITY_ICONS = {
  critical: AlertCircle,
  high:     AlertTriangle,
  medium:   AlertTriangle,
  low:      AlertCircle,
};

function SeverityBadge({ severity }) {
  const cls = SEVERITY_COLORS[severity] || "text-slate-400 bg-slate-800 border-slate-700";
  return <span className={`text-[10px] px-2 py-0.5 border font-medium ${cls}`}>{severity}</span>;
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
        className="border-t border-[#1a3050] hover:bg-[#1a3050]/30 cursor-pointer"
        onClick={() => setExpanded((v) => !v)}
      >
        <td className="px-3 py-2">
          <Icon size={12} className={
            err.severity === "critical" ? "text-red-400" :
            err.severity === "high" ? "text-orange-400" :
            err.severity === "medium" ? "text-yellow-400" : "text-blue-400"
          } />
        </td>
        <td className="px-3 py-2"><SeverityBadge severity={err.severity} /></td>
        <td className="px-3 py-2 text-slate-400 text-[10px]">{err.category}</td>
        <td className="px-3 py-2 text-white max-w-xs truncate">{err.message}</td>
        <td className="px-3 py-2 text-slate-400 text-[10px]">{err.endpoint || "—"}</td>
        <td className="px-3 py-2 text-slate-400">{err.frequency}</td>
        <td className="px-3 py-2 text-slate-400 text-[10px]">{(err.last_seen || "").slice(0, 16)}</td>
        <td className="px-3 py-2">
          {err.resolved ? (
            <CheckCircle size={12} className="text-green-400" />
          ) : (
            <X size={12} className="text-red-400" />
          )}
        </td>
      </tr>
      {expanded && (
        <tr className="border-t border-[#1a3050] bg-[#080f1f]">
          <td colSpan={8} className="px-4 py-4">
            <div className="space-y-3">
              {err.stack_trace && (
                <div>
                  <div className="text-[10px] text-slate-500 mb-1">Stack Trace</div>
                  <pre className="text-[10px] text-slate-300 bg-[#0B1C35] p-3 overflow-x-auto max-h-48 border border-[#1a3050]">
                    {err.stack_trace}
                  </pre>
                </div>
              )}
              <div className="flex items-end gap-3 flex-wrap">
                <div>
                  <div className="text-[10px] text-slate-500 mb-1">Assign to</div>
                  <input
                    type="text"
                    value={owner}
                    onChange={(e) => setOwner(e.target.value)}
                    placeholder="email or name"
                    className="text-xs bg-[#0B1C35] border border-[#1a3050] text-slate-300 px-2 py-1 w-40"
                  />
                </div>
                <div>
                  <div className="text-[10px] text-slate-500 mb-1">Remediation Note</div>
                  <input
                    type="text"
                    value={note}
                    onChange={(e) => setNote(e.target.value)}
                    placeholder="What was fixed?"
                    className="text-xs bg-[#0B1C35] border border-[#1a3050] text-slate-300 px-2 py-1 w-64"
                  />
                </div>
                {!err.resolved && (
                  <button
                    onClick={resolve}
                    disabled={resolving}
                    className="text-xs bg-green-700 hover:bg-green-600 disabled:opacity-50 text-white px-3 py-1 transition-colors flex items-center gap-1"
                  >
                    <CheckCircle size={11} />
                    {resolving ? "Resolving..." : "Mark Resolved"}
                  </button>
                )}
                <div className="text-[10px] text-slate-500">
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
          <button
            onClick={() => window.open("/api/admin/aos/errors/export", "_blank")}
            className="flex items-center gap-1.5 text-xs bg-[#0F2847] border border-[#1a3050] text-slate-300 px-3 py-1.5 hover:text-white transition-colors"
          >
            <Download size={12} />
            Export CSV
          </button>
          <button onClick={refresh} className="p-1.5 bg-[#0F2847] border border-[#1a3050] text-slate-400 hover:text-white">
            <RefreshCw size={14} className={loading ? "animate-spin" : ""} />
          </button>
        </div>
      }
    >

      {/* Stats */}
      {stats && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <div className="bg-[#0F2847] border border-[#1a3050] p-3">
            <div className="text-xl font-bold text-white">{stats.unresolved}</div>
            <div className="text-xs text-slate-400">Unresolved</div>
          </div>
          <div className="bg-[#0F2847] border border-red-700/50 p-3">
            <div className="text-xl font-bold text-red-400">{stats.critical}</div>
            <div className="text-xs text-slate-400">Critical (open)</div>
          </div>
          <div className="bg-[#0F2847] border border-[#1a3050] p-3">
            <div className="text-xl font-bold text-yellow-400">{stats.new_24h}</div>
            <div className="text-xs text-slate-400">New (24h)</div>
          </div>
          <div className="bg-[#0F2847] border border-[#1a3050] p-3 space-y-1">
            {(stats.by_severity || []).slice(0, 3).map((s) => (
              <div key={s.severity} className="flex justify-between text-xs">
                <span className="text-slate-400">{s.severity}</span>
                <span className="text-white">{s.count}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Category breakdown */}
      {stats?.by_category && (
        <div className="bg-[#0F2847] border border-[#1a3050] p-4">
          <div className="text-xs font-semibold text-slate-400 mb-2">By Category</div>
          <div className="flex flex-wrap gap-2">
            {stats.by_category.map((c) => (
              <button
                key={c.category}
                onClick={() => setCategory(category === c.category ? "" : c.category)}
                className={`text-xs px-2 py-1 border transition-colors ${
                  category === c.category
                    ? "bg-blue-600 border-blue-500 text-white"
                    : "bg-[#0B1C35] border-[#1a3050] text-slate-300 hover:text-white"
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
        <select
          value={severity}
          onChange={(e) => { setSeverity(e.target.value); setPage(1); }}
          className="text-xs bg-[#0F2847] border border-[#1a3050] text-slate-300 px-2 py-1.5"
        >
          <option value="">All Severities</option>
          <option value="critical">Critical</option>
          <option value="high">High</option>
          <option value="medium">Medium</option>
          <option value="low">Low</option>
        </select>
        <select
          value={category}
          onChange={(e) => { setCategory(e.target.value); setPage(1); }}
          className="text-xs bg-[#0F2847] border border-[#1a3050] text-slate-300 px-2 py-1.5"
        >
          <option value="">All Categories</option>
          <option value="frontend">Frontend</option>
          <option value="backend">Backend</option>
          <option value="api">API</option>
          <option value="database">Database</option>
          <option value="payment">Payment</option>
          <option value="auth">Auth</option>
          <option value="email">Email</option>
        </select>
        <select
          value={resolved}
          onChange={(e) => { setResolved(e.target.value); setPage(1); }}
          className="text-xs bg-[#0F2847] border border-[#1a3050] text-slate-300 px-2 py-1.5"
        >
          <option value="">All Statuses</option>
          <option value="false">Unresolved</option>
          <option value="true">Resolved</option>
        </select>
        <span className="text-xs text-slate-500 ml-2">{total} errors</span>
      </div>

      {/* Error table */}
      <div className="bg-[#0F2847] border border-[#1a3050] overflow-x-auto">
        <table className="w-full text-xs text-slate-300">
          <thead className="text-slate-500 border-b border-[#1a3050]">
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
              <tr><td colSpan={8} className="px-3 py-8 text-center text-slate-500">Loading...</td></tr>
            )}
            {!loading && items.map((err) => (
              <ErrorRow key={err.id} err={err} onUpdate={refresh} />
            ))}
            {!loading && items.length === 0 && (
              <tr>
                <td colSpan={8} className="px-3 py-8 text-center text-slate-500">
                  <CheckCircle size={24} className="text-green-400 mx-auto mb-2" />
                  No errors matching current filters
                </td>
              </tr>
            )}
          </tbody>
        </table>
        <div className="flex items-center justify-between px-3 py-2 border-t border-[#1a3050]">
          <span className="text-xs text-slate-500">{total} total · Click any row to expand</span>
          <div className="flex gap-2">
            <button disabled={page <= 1} onClick={() => setPage((p) => p - 1)} className="text-xs text-slate-400 hover:text-white disabled:opacity-40 px-2 py-1 bg-[#0B1C35] border border-[#1a3050]">Prev</button>
            <span className="text-xs text-slate-400 px-2 py-1">Page {page}</span>
            <button disabled={items.length < 50} onClick={() => setPage((p) => p + 1)} className="text-xs text-slate-400 hover:text-white disabled:opacity-40 px-2 py-1 bg-[#0B1C35] border border-[#1a3050]">Next</button>
          </div>
        </div>
      </div>
    </AdministrationLayout>
  );
}
