import React, { useState, useEffect, useCallback } from "react";
import {
  Shield, ShieldAlert, ShieldCheck, Lock, Globe, Laptop,
  Activity, AlertTriangle, CheckCircle2, XCircle, RefreshCw,
  Trash2, LogOut, Zap, Plus, Eye, FileText, Star, Award,
  Cpu, Radio, Map, Clock, Server,
} from "lucide-react";
import api from "@/lib/api";
import { NAVY, WARM, BRD } from "@/lib/tokens";
import { AdministrationLayout } from "@/layouts";

// ── data hook ─────────────────────────────────────────────────────────────────
function useApi(path, deps = []) {
  const [data, setData]       = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError]     = useState(null);
  const fetch = useCallback(async () => {
    setLoading(true); setError(null);
    try { const r = await api.get(path); setData(r.data); }
    catch (e) { setError(e?.response?.data?.detail || "Failed"); }
    finally { setLoading(false); }
  }, [path, ...deps]);
  return { data, loading, error, fetch };
}

const SEV_COLOURS = {
  critical: "bg-red-100 text-red-700 border border-red-300",
  high:     "bg-orange-100 text-orange-700 border border-orange-300",
  medium:   "bg-amber-100 text-amber-700 border border-amber-300",
  low:      "bg-blue-100 text-blue-700 border border-blue-300",
};
const sevPill = (sev) => (
  <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${SEV_COLOURS[sev] || "bg-slate-100 text-slate-600"}`}>{sev}</span>
);

// ─────────────────────────────────────────────────────────────────────────────
// TAB: Devices
// ─────────────────────────────────────────────────────────────────────────────
function DevicesTab() {
  const { data, loading, error, fetch } = useApi("/api/admin/hardening/devices");
  useEffect(() => { fetch(); }, []);

  const revoke = async (id) => {
    await api.delete(`/admin/hardening/devices/${id}`);
    fetch();
  };
  const revokeAll = async () => {
    if (!window.confirm("Revoke ALL trusted devices? You will need to complete MFA on next login from every device.")) return;
    await api.delete("/admin/hardening/devices");
    fetch();
  };

  if (loading) return <div className="text-sm text-slate-400 animate-pulse">Loading devices…</div>;
  if (error)   return <div className="text-sm text-red-500">{error}</div>;

  const devices = data?.devices || [];
  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <p className="text-sm text-slate-600">Trusted devices bypass the MFA challenge on subsequent logins.</p>
        {devices.length > 0 && (
          <button onClick={revokeAll} className="text-xs text-red-600 hover:underline flex items-center gap-1">
            <Trash2 className="w-3 h-3" /> Revoke All
          </button>
        )}
      </div>

      {devices.length === 0 ? (
        <div className="text-center py-8 text-slate-400 text-sm">No trusted devices</div>
      ) : (
        <div className="space-y-2">
          {devices.map(d => (
            <div key={d.id} className="flex items-center justify-between bg-white border border-slate-200 rounded-md p-3">
              <div className="flex items-center gap-3">
                <Laptop className="w-5 h-5 text-slate-400 flex-shrink-0" />
                <div>
                  <div className="text-sm font-medium text-slate-800">{d.browser} on {d.os}</div>
                  <div className="text-xs text-slate-500">{d.ip}{d.country ? ` · ${d.country}` : ""}{d.city ? `, ${d.city}` : ""}</div>
                  <div className="text-xs text-slate-400">Last seen: {d.last_seen_at ? new Date(d.last_seen_at).toLocaleString() : "—"}</div>
                </div>
              </div>
              <button onClick={() => revoke(d.id)} className="text-xs text-red-500 hover:text-red-700 px-2 py-1 rounded hover:bg-red-50">
                Revoke
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// TAB: Sessions
// ─────────────────────────────────────────────────────────────────────────────
function SessionsTab() {
  const { data, loading, error, fetch } = useApi("/api/admin/hardening/sessions");
  useEffect(() => { fetch(); }, []);

  const terminate = async (id) => {
    await api.post("/admin/hardening/sessions/terminate", { session_id: id });
    fetch();
  };
  const terminateAll = async () => {
    if (!window.confirm("Terminate all active sessions? You will be logged out.")) return;
    await api.post("/admin/hardening/sessions/terminate-all");
    fetch();
  };
  const emergencyLogout = async () => {
    if (!window.confirm("Emergency logout will revoke ALL sessions AND all trusted devices. Proceed?")) return;
    await api.post("/admin/hardening/sessions/emergency-logout");
    window.location.href = "/login";
  };

  if (loading) return <div className="text-sm text-slate-400 animate-pulse">Loading sessions…</div>;
  if (error)   return <div className="text-sm text-red-500">{error}</div>;

  const sessions = data?.sessions || [];
  return (
    <div className="space-y-4">
      <div className="flex flex-wrap gap-2 justify-between items-center">
        <p className="text-sm text-slate-600">{sessions.length} active session(s)</p>
        <div className="flex gap-2">
          {sessions.length > 0 && (
            <button onClick={terminateAll} className="px-3 py-1.5 text-xs bg-slate-100 text-slate-700 rounded-lg hover:bg-slate-200 flex items-center gap-1">
              <LogOut className="w-3 h-3" /> Terminate All
            </button>
          )}
          <button onClick={emergencyLogout} className="px-3 py-1.5 text-xs bg-red-600 text-white rounded-lg hover:bg-red-700 flex items-center gap-1">
            <Zap className="w-3 h-3" /> Emergency Logout
          </button>
        </div>
      </div>

      {sessions.length === 0 ? (
        <div className="text-center py-8 text-slate-400 text-sm">No active sessions</div>
      ) : (
        <div className="overflow-x-auto rounded-md border border-slate-200">
          <table className="w-full text-sm">
            <thead className="bg-slate-50 border-b border-slate-200">
              <tr>
                <th className="text-left p-3 text-xs text-slate-500 font-medium">IP</th>
                <th className="text-left p-3 text-xs text-slate-500 font-medium">Device</th>
                <th className="text-left p-3 text-xs text-slate-500 font-medium">Issued</th>
                <th className="text-left p-3 text-xs text-slate-500 font-medium">Expires</th>
                <th className="p-3"></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {sessions.map(s => (
                <tr key={s.id}>
                  <td className="p-3 font-mono text-xs">{s.ip || "—"}</td>
                  <td className="p-3 text-xs">{s.device_info || "Unknown"}</td>
                  <td className="p-3 text-xs text-slate-500">{s.issued_at ? new Date(s.issued_at).toLocaleString() : "—"}</td>
                  <td className="p-3 text-xs text-slate-500">{s.expires_at ? new Date(s.expires_at).toLocaleString() : "—"}</td>
                  <td className="p-3 text-right">
                    <button onClick={() => terminate(s.id)} className="text-xs text-red-500 hover:underline">Terminate</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// TAB: IP Allowlist
// ─────────────────────────────────────────────────────────────────────────────
function IPAllowlistTab() {
  const { data, loading, error, fetch } = useApi("/api/admin/hardening/ip-allowlist");
  const [ip, setIp]       = useState("");
  const [label, setLabel] = useState("");
  const [saving, setSaving] = useState(false);
  const [addErr, setAddErr] = useState("");
  useEffect(() => { fetch(); }, []);

  const add = async () => {
    if (!ip.trim()) return;
    setSaving(true); setAddErr("");
    try {
      await api.post("/admin/hardening/ip-allowlist", { ip: ip.trim(), label: label.trim() });
      setIp(""); setLabel(""); fetch();
    } catch (e) {
      setAddErr(e?.response?.data?.detail || "Failed to add");
    } finally { setSaving(false); }
  };

  const remove = async (id) => {
    await api.delete(`/admin/hardening/ip-allowlist/${id}`);
    fetch();
  };

  const setMode = async (mode) => {
    await api.patch("/admin/hardening/ip-allowlist/mode", { mode });
    fetch();
  };

  if (loading) return <div className="text-sm text-slate-400 animate-pulse">Loading allowlist…</div>;

  const entries = data?.entries || [];
  const mode    = data?.mode || "monitor";

  return (
    <div className="space-y-4">
      {/* Mode selector */}
      <div className="flex items-center gap-3 p-3 bg-slate-50 rounded-md">
        <Globe className="w-4 h-4 text-slate-500" />
        <span className="text-sm text-slate-700 font-medium">Allowlist Mode:</span>
        <button
          onClick={() => setMode("monitor")}
          className={`px-3 py-1 text-xs rounded-full border font-medium transition-colors ${mode === "monitor" ? "bg-blue-100 text-blue-700 border-blue-300" : "bg-white text-slate-500 border-slate-200 hover:bg-slate-50"}`}
        >
          Monitor (log only)
        </button>
        <button
          onClick={() => setMode("enforce")}
          className={`px-3 py-1 text-xs rounded-full border font-medium transition-colors ${mode === "enforce" ? "bg-red-100 text-red-700 border-red-300" : "bg-white text-slate-500 border-slate-200 hover:bg-slate-50"}`}
        >
          Enforce (block)
        </button>
        <span className="text-xs text-slate-400 ml-auto">
          {mode === "enforce" ? "Non-allowlisted IPs will be blocked" : "Non-allowlisted IPs will be logged"}
        </span>
      </div>

      {/* Add form */}
      <div className="flex gap-2 flex-wrap">
        <input
          type="text"
          placeholder="IP or CIDR (e.g. 192.168.1.0/24)"
          value={ip}
          onChange={e => setIp(e.target.value)}
          className="flex-1 min-w-48 border border-slate-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
        />
        <input
          type="text"
          placeholder="Label (optional)"
          value={label}
          onChange={e => setLabel(e.target.value)}
          className="w-40 border border-slate-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
        />
        <button
          onClick={add}
          disabled={saving || !ip.trim()}
          className="px-4 py-2 bg-indigo-600 text-white text-sm rounded-lg hover:bg-indigo-700 disabled:opacity-50 flex items-center gap-1"
        >
          <Plus className="w-4 h-4" /> {saving ? "Adding…" : "Add"}
        </button>
      </div>
      {addErr && <div className="text-xs text-red-600">{addErr}</div>}

      {entries.length === 0 ? (
        <div className="text-center py-6 text-slate-400 text-sm">No IP allowlist entries. All IPs are {mode === "enforce" ? "BLOCKED" : "allowed (monitor mode)"}.</div>
      ) : (
        <div className="rounded-md border border-slate-200 overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-slate-50 border-b border-slate-200">
              <tr>
                <th className="text-left p-3 text-xs text-slate-500 font-medium">IP / CIDR</th>
                <th className="text-left p-3 text-xs text-slate-500 font-medium">Label</th>
                <th className="text-left p-3 text-xs text-slate-500 font-medium">Added</th>
                <th className="p-3"></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {entries.map(e => (
                <tr key={e.id}>
                  <td className="p-3 font-mono text-xs">{e.ip}</td>
                  <td className="p-3 text-xs text-slate-600">{e.label}</td>
                  <td className="p-3 text-xs text-slate-400">{e.added_at ? e.added_at.slice(0, 10) : "—"}</td>
                  <td className="p-3 text-right">
                    <button onClick={() => remove(e.id)} className="text-xs text-red-500 hover:underline">Remove</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// TAB: Break-Glass Recovery
// ─────────────────────────────────────────────────────────────────────────────
function BreakGlassTab() {
  const { data: history, loading: histLoading, fetch: fetchHistory } = useApi("/api/admin/hardening/break-glass/history");
  const [reason, setReason]   = useState("");
  const [token, setToken]     = useState(null);
  const [genLoading, setGenLoading] = useState(false);
  const [genError, setGenError]   = useState("");
  useEffect(() => { fetchHistory(); }, []);

  const generate = async () => {
    if (!reason.trim()) { setGenError("Reason is required"); return; }
    setGenLoading(true); setGenError("");
    try {
      const r = await api.post("/admin/hardening/break-glass/initiate", { reason: reason.trim() });
      setToken(r.data);
      fetchHistory();
    } catch (e) {
      setGenError(e?.response?.data?.detail || "Failed");
    } finally { setGenLoading(false); }
  };

  return (
    <div className="space-y-5">
      <div className="bg-amber-50 border border-amber-200 rounded-md p-4 text-sm text-amber-800">
        <strong>Break-Glass Recovery</strong> generates a 15-minute token that can reset MFA or unlock the admin account without a normal authentication session. Use only in emergencies.
      </div>

      {token ? (
        <div className="bg-slate-900 rounded-xl p-5 space-y-3">
          <div className="text-green-400 font-semibold text-sm">Recovery Token Generated</div>
          <code className="block text-green-300 text-sm font-mono break-all select-all bg-slate-800 rounded-lg p-3">
            {token.recovery_token}
          </code>
          <div className="text-slate-400 text-xs">Expires: {token.expires_at ? new Date(token.expires_at).toLocaleString() : "—"}</div>
          <div className="text-red-400 text-xs">{token.warning}</div>
          <button onClick={() => setToken(null)} className="text-xs text-slate-400 hover:text-slate-300">Clear</button>
        </div>
      ) : (
        <div className="space-y-3">
          <div className="font-medium text-slate-800 text-sm">Generate Emergency Recovery Token</div>
          <textarea
            placeholder="Reason for break-glass access (required for audit trail)…"
            value={reason}
            onChange={e => setReason(e.target.value)}
            rows={2}
            className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-amber-400 resize-none"
          />
          {genError && <div className="text-xs text-red-600">{genError}</div>}
          <button
            onClick={generate}
            disabled={genLoading || !reason.trim()}
            className="px-4 py-2 bg-amber-600 text-white text-sm rounded-lg hover:bg-amber-700 disabled:opacity-50 flex items-center gap-2"
          >
            <Zap className="w-4 h-4" /> {genLoading ? "Generating…" : "Generate Recovery Token"}
          </button>
        </div>
      )}

      {/* History */}
      <div>
        <div className="font-medium text-slate-800 text-sm mb-2">Break-Glass History</div>
        {histLoading ? (
          <div className="text-xs text-slate-400 animate-pulse">Loading…</div>
        ) : (history?.events || []).length === 0 ? (
          <div className="text-xs text-slate-400">No break-glass events on record.</div>
        ) : (
          <div className="space-y-2">
            {(history?.events || []).map(e => (
              <div key={e.id} className={`rounded-lg border p-3 text-xs ${e.used ? "border-slate-200 bg-slate-50" : "border-amber-200 bg-amber-50"}`}>
                <div className="flex justify-between mb-1">
                  <span className="font-medium text-slate-700">{e.reason}</span>
                  <span className={`px-2 py-0.5 rounded-full ${e.used ? "bg-slate-200 text-slate-600" : "bg-amber-100 text-amber-700"}`}>
                    {e.used ? `Used: ${e.action}` : "Not used"}
                  </span>
                </div>
                <div className="text-slate-400">{e.created_at ? new Date(e.created_at).toLocaleString() : "—"} · {e.actor_email}</div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// TAB: Security Events
// ─────────────────────────────────────────────────────────────────────────────
function SecurityEventsTab() {
  const [severity, setSeverity] = useState("");
  const [resolved, setResolved] = useState(undefined);
  const [resolveNote, setResolveNote] = useState("");
  const [resolvingId, setResolvingId] = useState(null);
  const { data, loading, error, fetch } = useApi(
    `/api/admin/hardening/security-events?${severity ? `severity=${severity}&` : ""}${resolved !== undefined ? `resolved=${resolved}&` : ""}limit=50`
  );
  useEffect(() => { fetch(); }, [severity, resolved]);

  const resolve = async (id) => {
    await api.post(`/admin/hardening/security-events/${id}/resolve`, { note: resolveNote });
    setResolvingId(null); setResolveNote(""); fetch();
  };

  const stats = data?.stats || {};
  const events = data?.events || [];

  return (
    <div className="space-y-4">
      {/* Stats */}
      <div className="grid grid-cols-4 gap-3">
        {["critical", "high", "medium", "low"].map(s => {
          const d = stats.by_severity?.[s] || {};
          return (
            <div key={s} className={`rounded-md p-3 text-center border ${s === "critical" ? "border-red-200 bg-red-50" : s === "high" ? "border-orange-200 bg-orange-50" : s === "medium" ? "border-amber-100 bg-amber-50" : "border-blue-100 bg-blue-50"}`}>
              <div className={`text-xl font-bold ${s === "critical" ? "text-red-700" : s === "high" ? "text-orange-700" : s === "medium" ? "text-amber-700" : "text-blue-700"}`}>
                {d.unresolved || 0}
              </div>
              <div className="text-xs text-slate-500 capitalize">{s} unresolved</div>
              <div className="text-xs text-slate-400">{d.total || 0} total</div>
            </div>
          );
        })}
      </div>

      {/* Filters */}
      <div className="flex gap-2 flex-wrap">
        <select
          value={severity}
          onChange={e => setSeverity(e.target.value)}
          className="border border-slate-300 rounded-lg px-3 py-1.5 text-sm focus:outline-none"
        >
          <option value="">All Severities</option>
          {["critical", "high", "medium", "low"].map(s => <option key={s} value={s}>{s}</option>)}
        </select>
        <select
          value={resolved === undefined ? "" : String(resolved)}
          onChange={e => setResolved(e.target.value === "" ? undefined : e.target.value === "true")}
          className="border border-slate-300 rounded-lg px-3 py-1.5 text-sm focus:outline-none"
        >
          <option value="">All Events</option>
          <option value="false">Unresolved</option>
          <option value="true">Resolved</option>
        </select>
        <button onClick={fetch} className="px-3 py-1.5 bg-slate-100 text-slate-700 text-sm rounded-lg hover:bg-slate-200 flex items-center gap-1">
          <RefreshCw className="w-3 h-3" /> Refresh
        </button>
      </div>

      {/* Events list */}
      {loading ? (
        <div className="text-sm text-slate-400 animate-pulse">Loading events…</div>
      ) : events.length === 0 ? (
        <div className="text-center py-8 text-slate-400 text-sm">No security events found</div>
      ) : (
        <div className="space-y-2">
          {events.map(e => (
            <div key={e.id} className={`rounded-md border p-3 ${e.resolved ? "border-slate-200 bg-slate-50 opacity-70" : "border-slate-200 bg-white"}`}>
              <div className="flex items-start justify-between gap-2">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    {sevPill(e.severity)}
                    <span className="text-sm font-medium text-slate-800">{e.event_type}</span>
                    {e.resolved && <span className="text-xs text-green-600 bg-green-50 px-2 py-0.5 rounded-full">resolved</span>}
                  </div>
                  <div className="text-xs text-slate-500">
                    {e.ip && <span className="mr-2">IP: {e.ip}</span>}
                    {e.actor_email && <span className="mr-2">Actor: {e.actor_email}</span>}
                    <span>{e.created_at ? new Date(e.created_at).toLocaleString() : "—"}</span>
                  </div>
                  {e.extra && Object.keys(e.extra).length > 0 && (
                    <div className="text-xs text-slate-400 mt-1 font-mono">{JSON.stringify(e.extra).slice(0, 150)}</div>
                  )}
                  {e.resolved && e.resolution_note && (
                    <div className="text-xs text-green-600 mt-1">Note: {e.resolution_note}</div>
                  )}
                </div>
                {!e.resolved && (
                  resolvingId === e.id ? (
                    <div className="flex gap-1 flex-shrink-0">
                      <input
                        type="text"
                        placeholder="Resolution note"
                        value={resolveNote}
                        onChange={ev => setResolveNote(ev.target.value)}
                        className="w-32 border border-slate-300 rounded px-2 py-1 text-xs"
                      />
                      <button onClick={() => resolve(e.id)} className="text-xs bg-green-600 text-white px-2 py-1 rounded hover:bg-green-700">OK</button>
                      <button onClick={() => setResolvingId(null)} className="text-xs text-slate-400 px-1">✕</button>
                    </div>
                  ) : (
                    <button onClick={() => setResolvingId(e.id)} className="text-xs text-indigo-600 hover:underline flex-shrink-0">
                      Resolve
                    </button>
                  )
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// TAB: Audit Log
// ─────────────────────────────────────────────────────────────────────────────
function AuditLogTab() {
  const [action, setAction]   = useState("");
  const [debouncedAction, setDebounced] = useState("");
  useEffect(() => {
    const t = setTimeout(() => setDebounced(action), 400);
    return () => clearTimeout(t);
  }, [action]);

  const { data, loading, fetch } = useApi(
    `/api/admin/hardening/audit?limit=100${debouncedAction ? `&action=${encodeURIComponent(debouncedAction)}` : ""}`
  );
  useEffect(() => { fetch(); }, [debouncedAction]);

  const { data: summary, fetch: fetchSummary } = useApi("/api/admin/hardening/audit/summary");
  useEffect(() => { fetchSummary(); }, []);

  const events = data?.events || [];

  return (
    <div className="space-y-4">
      {/* Summary */}
      {summary && (
        <div className="grid grid-cols-4 gap-3">
          <div className="bg-slate-50 border border-slate-200 rounded-md p-3 text-center">
            <div className="text-xl font-bold text-slate-700">{summary.total_last_24h}</div>
            <div className="text-xs text-slate-500">Events (24h)</div>
          </div>
          <div className="bg-slate-50 border border-slate-200 rounded-md p-3 text-center">
            <div className="text-xl font-bold text-slate-700">{summary.total_last_7d}</div>
            <div className="text-xs text-slate-500">Events (7d)</div>
          </div>
          <div className="bg-slate-50 border border-slate-200 rounded-md p-3 text-center">
            <div className="text-xl font-bold text-slate-700">{summary.login_events_total}</div>
            <div className="text-xs text-slate-500">Login Events</div>
          </div>
          <div className={`border rounded-md p-3 text-center ${summary.unresolved_security_events > 0 ? "border-red-200 bg-red-50" : "border-green-200 bg-green-50"}`}>
            <div className={`text-xl font-bold ${summary.unresolved_security_events > 0 ? "text-red-700" : "text-green-700"}`}>{summary.unresolved_security_events}</div>
            <div className="text-xs text-slate-500">Unresolved Events</div>
          </div>
        </div>
      )}

      <div className="flex gap-2">
        <input
          type="text"
          placeholder="Filter by action (e.g. auth.login)"
          value={action}
          onChange={e => setAction(e.target.value)}
          className="flex-1 border border-slate-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
        />
        <button onClick={fetch} className="px-3 py-2 bg-slate-100 text-slate-700 text-sm rounded-lg hover:bg-slate-200">
          <RefreshCw className="w-4 h-4" />
        </button>
      </div>

      {loading ? (
        <div className="text-sm text-slate-400 animate-pulse">Loading audit log…</div>
      ) : (
        <div className="rounded-md border border-slate-200 overflow-hidden">
          <table className="w-full text-xs">
            <thead className="bg-slate-50 border-b border-slate-200">
              <tr>
                <th className="text-left p-2 text-slate-500 font-medium">Action</th>
                <th className="text-left p-2 text-slate-500 font-medium">Actor</th>
                <th className="text-left p-2 text-slate-500 font-medium">IP</th>
                <th className="text-left p-2 text-slate-500 font-medium">When</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {events.map(e => (
                <tr key={e.id} className="hover:bg-slate-50">
                  <td className="p-2 font-mono text-slate-700">{e.action}</td>
                  <td className="p-2 text-slate-500">{e.actor_email || "—"}</td>
                  <td className="p-2 font-mono text-slate-400">{e.ip || "—"}</td>
                  <td className="p-2 text-slate-400">{e.created_at ? new Date(e.created_at).toLocaleString() : "—"}</td>
                </tr>
              ))}
              {events.length === 0 && (
                <tr><td colSpan={4} className="p-4 text-center text-slate-400">No events found</td></tr>
              )}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// TAB: Certification
// ─────────────────────────────────────────────────────────────────────────────
function CertificationTab() {
  const { data, loading, error, fetch } = useApi("/api/admin/hardening/certification");
  useEffect(() => { fetch(); }, []);

  if (loading) return <div className="text-sm text-slate-400 animate-pulse">Computing certification scores…</div>;
  if (error)   return <div className="text-sm text-red-500">{error}</div>;
  if (!data)   return null;

  const { scores, overall, grade, grade_color, certified, certification_label, checks } = data;

  const SCORE_LABELS = {
    authentication: "Authentication Security",
    authorization:  "Authorization Security",
    auditability:   "Auditability",
    session_security: "Session Security",
    recovery_readiness: "Recovery Readiness",
    privilege_escalation_resistance: "Privilege Escalation Resistance",
    zero_trust_readiness: "Zero-Trust Readiness",
  };

  const scoreColor = (s) => {
    if (s >= 90) return "text-green-700 bg-green-100";
    if (s >= 70) return "text-amber-700 bg-amber-100";
    return "text-red-700 bg-red-100";
  };

  const barColor = (s) => {
    if (s >= 90) return "bg-green-500";
    if (s >= 70) return "bg-amber-500";
    return "bg-red-500";
  };

  return (
    <div className="space-y-6">
      {/* Overall score */}
      <div className={`rounded-md border-2 p-6 text-center ${certified ? "border-green-300 bg-gradient-to-br from-green-50 to-emerald-50" : "border-amber-300 bg-gradient-to-br from-amber-50 to-yellow-50"}`}>
        <div className={`text-7xl font-black mb-1 ${grade_color === "green" ? "text-green-700" : grade_color === "lime" ? "text-lime-600" : grade_color === "yellow" ? "text-amber-600" : grade_color === "orange" ? "text-orange-600" : "text-red-700"}`}>
          {grade}
        </div>
        <div className="text-3xl font-bold text-slate-800 mb-2">{overall}/100</div>
        <div className={`text-sm font-semibold px-4 py-1 rounded-full inline-block ${certified ? "bg-green-100 text-green-800" : "bg-amber-100 text-amber-800"}`}>
          {certification_label}
        </div>
        <div className="text-xs text-slate-400 mt-2">Evaluated: {data.evaluated_at ? new Date(data.evaluated_at).toLocaleString() : "—"}</div>
      </div>

      {/* Score breakdown */}
      <div className="space-y-3">
        {Object.entries(scores).map(([key, score]) => (
          <div key={key}>
            <div className="flex items-center justify-between mb-1">
              <span className="text-sm text-slate-700">{SCORE_LABELS[key] || key}</span>
              <span className={`text-xs font-bold px-2 py-0.5 rounded-full ${scoreColor(score)}`}>{score}</span>
            </div>
            <div className="h-2 bg-slate-100 rounded-full overflow-hidden">
              <div className={`h-full ${barColor(score)} rounded-full transition-all`} style={{ width: `${score}%` }} />
            </div>
            {/* Checks for this section */}
            {checks && checks[key.replace("_security", "").replace("_readiness", "").replace("_resistance", "").replace("zero_trust", "zero_trust").replace("privilege_escalation", "privilege")] && (
              <div className="mt-1 space-y-0.5 pl-2">
                {(checks[key.replace("_security", "").replace("_readiness", "").replace("_resistance", "").replace("privilege_escalation", "privilege")] || []).slice(0, 4).map((c, i) => (
                  <div key={i} className={`text-xs flex items-center gap-1 ${c[1] ? "text-slate-500" : "text-amber-700"}`}>
                    <span>{c[0]}</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        ))}
      </div>

      <button onClick={fetch} className="w-full py-2 text-sm bg-slate-100 text-slate-700 rounded-lg hover:bg-slate-200 flex items-center justify-center gap-2">
        <RefreshCw className="w-4 h-4" /> Recalculate
      </button>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Main page
// ─────────────────────────────────────────────────────────────────────────────
const TABS = [
  { id: "sessions",    label: "Sessions",      icon: Activity },
  { id: "devices",     label: "Devices",       icon: Laptop },
  { id: "ip",          label: "IP Allowlist",  icon: Globe },
  { id: "events",      label: "Security Events", icon: ShieldAlert },
  { id: "audit",       label: "Audit Log",     icon: FileText },
  { id: "breakglass",  label: "Break-Glass",   icon: Zap },
  { id: "cert",        label: "Certification", icon: Award },
];

export default function AdminSecurityHardening() {
  const [tab, setTab] = useState("events");

  return (
    <AdministrationLayout
      title="Security Hardening Center"
      subtitle="Zero-trust session management, device trust, IP allowlist, security events, and certification"
      icon={<Shield className="w-5 h-5" />}
    >
      {/* Tab bar */}
      <div className="flex gap-1 overflow-x-auto border-b border-slate-200 pb-0">
        {TABS.map(({ id, label, icon: Icon }) => (
          <button
            key={id}
            onClick={() => setTab(id)}
            className={`px-3 py-2 text-sm font-medium whitespace-nowrap flex items-center gap-1.5 rounded-t-lg border-b-2 transition-colors flex-shrink-0
              ${tab === id
                ? "border-slate-900 text-slate-900 bg-slate-50"
                : "border-transparent text-slate-500 hover:text-slate-700"}`}
          >
            <Icon className="w-3.5 h-3.5" />
            {label}
          </button>
        ))}
      </div>

      {/* Tab content */}
      <div>
        {tab === "sessions"   && <SessionsTab />}
        {tab === "devices"    && <DevicesTab />}
        {tab === "ip"         && <IPAllowlistTab />}
        {tab === "events"     && <SecurityEventsTab />}
        {tab === "audit"      && <AuditLogTab />}
        {tab === "breakglass" && <BreakGlassTab />}
        {tab === "cert"       && <CertificationTab />}
      </div>
    </AdministrationLayout>
  );
}
