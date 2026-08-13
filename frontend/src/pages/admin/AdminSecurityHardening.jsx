import React, { useState, useEffect, useCallback } from "react";
import {
  Shield, ShieldAlert, ShieldCheck, Lock, Globe, Laptop,
  Activity, AlertTriangle, CheckCircle2, XCircle, RefreshCw,
  Trash2, LogOut, Zap, Plus, Eye, FileText, Star, Award,
  Cpu, Radio, Map, Clock, Server,
} from "lucide-react";
import api from "@/lib/api";
import { NAVY, WARM, BRD, EMERALD, AMBER, CRIMSON } from "@/lib/tokens";
import { AdministrationLayout } from "@/layouts";
import {
  Card, Button, Input, Textarea, FormSelect, Badge, Alert,
  NavTabs, DataTable, StatCard, StatGrid, ProgressBar,
} from "@/components/ds";
import { confirmDialog } from "@/lib/confirm";

// ── data hook ─────────────────────────────────────────────────────────────────
function useApi(path) {
  const [data, setData]       = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError]     = useState(null);
  const fetch = useCallback(async () => {
    setLoading(true); setError(null);
    try { const r = await api.get(path); setData(r.data); }
    catch (e) { setError(e?.response?.data?.detail || "Failed"); }
    finally { setLoading(false); }
  }, [path]);
  return { data, loading, error, fetch };
}

const SEV_BADGE = {
  critical: "danger",
  high:     "warning",
  medium:   "warning",
  low:      "info",
};
const sevPill = (sev) => <Badge variant={SEV_BADGE[sev] || "neutral"} size="sm">{sev}</Badge>;

// ─────────────────────────────────────────────────────────────────────────────
// TAB: Devices
// ─────────────────────────────────────────────────────────────────────────────
function DevicesTab() {
  const { data, loading, error, fetch } = useApi("/api/admin/hardening/devices");
  useEffect(() => { fetch(); }, [fetch]);

  const revoke = async (id) => {
    await api.delete(`/admin/hardening/devices/${id}`);
    fetch();
  };
  const revokeAll = async () => {
    if (!(await confirmDialog({ title: "Revoke ALL trusted devices? You will need to complete MFA on next login from every device.", danger: true }))) return;
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
          <Button variant="link" size="sm" onClick={revokeAll} className="!text-red-600">
            <Trash2 className="w-3 h-3" /> Revoke All
          </Button>
        )}
      </div>

      {devices.length === 0 ? (
        <div className="text-center py-8 text-slate-400 text-sm">No trusted devices</div>
      ) : (
        <div className="space-y-2">
          {devices.map(d => (
            <Card key={d.id} padding="sm" className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <Laptop className="w-5 h-5 text-slate-400 flex-shrink-0" />
                <div>
                  <div className="text-sm font-medium text-slate-800">{d.browser} on {d.os}</div>
                  <div className="text-xs text-slate-500">{d.ip}{d.country ? ` · ${d.country}` : ""}{d.city ? `, ${d.city}` : ""}</div>
                  <div className="text-xs text-slate-400">Last seen: {d.last_seen_at ? new Date(d.last_seen_at).toLocaleString() : "—"}</div>
                </div>
              </div>
              <Button variant="ghost" size="sm" onClick={() => revoke(d.id)} className="!text-red-500">
                Revoke
              </Button>
            </Card>
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
  useEffect(() => { fetch(); }, [fetch]);

  const terminate = async (id) => {
    await api.post("/admin/hardening/sessions/terminate", { session_id: id });
    fetch();
  };
  const terminateAll = async () => {
    if (!(await confirmDialog({ title: "Terminate all active sessions? You will be logged out.", danger: false }))) return;
    await api.post("/admin/hardening/sessions/terminate-all");
    fetch();
  };
  const emergencyLogout = async () => {
    if (!(await confirmDialog({ title: "Emergency logout will revoke ALL sessions AND all trusted devices. Proceed?", danger: true }))) return;
    await api.post("/admin/hardening/sessions/emergency-logout");
    window.location.href = "/login";
  };

  if (loading) return <div className="text-sm text-slate-400 animate-pulse">Loading sessions…</div>;
  if (error)   return <div className="text-sm text-red-500">{error}</div>;

  const sessions = data?.sessions || [];

  const columns = [
    { key: "ip", label: "IP", render: (v) => <span className="font-mono text-xs">{v || "—"}</span> },
    { key: "device_info", label: "Device", render: (v) => <span className="text-xs">{v || "Unknown"}</span> },
    { key: "issued_at", label: "Issued", render: (v) => <span className="text-xs text-slate-500">{v ? new Date(v).toLocaleString() : "—"}</span> },
    { key: "expires_at", label: "Expires", render: (v) => <span className="text-xs text-slate-500">{v ? new Date(v).toLocaleString() : "—"}</span> },
    {
      key: "_actions", label: "", align: "right",
      render: (_, s) => <Button variant="link" size="sm" onClick={() => terminate(s.id)} className="!text-red-500">Terminate</Button>,
    },
  ];

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap gap-2 justify-between items-center">
        <p className="text-sm text-slate-600">{sessions.length} active session(s)</p>
        <div className="flex gap-2">
          {sessions.length > 0 && (
            <Button variant="subtle" size="sm" onClick={terminateAll}>
              <LogOut className="w-3 h-3" /> Terminate All
            </Button>
          )}
          <Button variant="danger" size="sm" onClick={emergencyLogout}>
            <Zap className="w-3 h-3" /> Emergency Logout
          </Button>
        </div>
      </div>

      <DataTable
        columns={columns}
        rows={sessions}
        emptyNode={<div className="text-center py-8 text-slate-400 text-sm">No active sessions</div>}
      />
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
  useEffect(() => { fetch(); }, [fetch]);

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

  const columns = [
    { key: "ip", label: "IP / CIDR", render: (v) => <span className="font-mono text-xs">{v}</span> },
    { key: "label", label: "Label", render: (v) => <span className="text-xs text-slate-600">{v}</span> },
    { key: "added_at", label: "Added", render: (v) => <span className="text-xs text-slate-400">{v ? v.slice(0, 10) : "—"}</span> },
    {
      key: "_actions", label: "", align: "right",
      render: (_, e) => <Button variant="link" size="sm" onClick={() => remove(e.id)} className="!text-red-500">Remove</Button>,
    },
  ];

  return (
    <div className="space-y-4">
      {/* Mode selector */}
      <Card padding="sm" className="flex items-center gap-3">
        <Globe className="w-4 h-4 text-slate-500" />
        <span className="text-sm text-slate-700 font-medium">Allowlist Mode:</span>
        <Button variant={mode === "monitor" ? "primary" : "ghost"} size="sm" onClick={() => setMode("monitor")}>
          Monitor (log only)
        </Button>
        <Button variant={mode === "enforce" ? "danger" : "ghost"} size="sm" onClick={() => setMode("enforce")}>
          Enforce (block)
        </Button>
        <span className="text-xs text-slate-400 ml-auto">
          {mode === "enforce" ? "Non-allowlisted IPs will be blocked" : "Non-allowlisted IPs will be logged"}
        </span>
      </Card>

      {/* Add form */}
      <div className="flex gap-2 flex-wrap items-start">
        <Input
          type="text"
          placeholder="IP or CIDR (e.g. 192.168.1.0/24)"
          value={ip}
          onChange={e => setIp(e.target.value)}
          wrapperClassName="flex-1 min-w-48 !mb-0"
        />
        <Input
          type="text"
          placeholder="Label (optional)"
          value={label}
          onChange={e => setLabel(e.target.value)}
          wrapperClassName="w-40 !mb-0"
        />
        <Button variant="primary" onClick={add} disabled={saving || !ip.trim()} loading={saving}>
          <Plus className="w-4 h-4" /> {saving ? "Adding…" : "Add"}
        </Button>
      </div>
      {addErr && <div className="text-xs text-red-600">{addErr}</div>}

      <DataTable
        columns={columns}
        rows={entries}
        emptyNode={
          <div className="text-center py-6 text-slate-400 text-sm">
            No IP allowlist entries. All IPs are {mode === "enforce" ? "BLOCKED" : "allowed (monitor mode)"}.
          </div>
        }
      />
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
  useEffect(() => { fetchHistory(); }, [fetchHistory]);

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
      <Alert variant="warning" title="Break-Glass Recovery">
        Generates a 15-minute token that can reset MFA or unlock the admin account without a normal
        authentication session. Use only in emergencies.
      </Alert>

      {token ? (
        // NOTE: kept as a dark "secret reveal" card (bg-slate-900) rather than
        // a light Card — same intentional terminal-style aesthetic used for
        // recovery codes elsewhere (e.g. AdminMFACenter), signalling "this is
        // a sensitive one-time secret" rather than ordinary page content.
        <div className="bg-slate-900 rounded-xl p-5 space-y-3">
          <div className="text-green-400 font-semibold text-sm">Recovery Token Generated</div>
          <code className="block text-green-300 text-sm font-mono break-all select-all bg-slate-800 rounded-lg p-3">
            {token.recovery_token}
          </code>
          <div className="text-slate-400 text-xs">Expires: {token.expires_at ? new Date(token.expires_at).toLocaleString() : "—"}</div>
          <div className="text-red-400 text-xs">{token.warning}</div>
          <Button variant="link" size="sm" onClick={() => setToken(null)} className="!text-slate-400">Clear</Button>
        </div>
      ) : (
        <div className="space-y-3">
          <div className="font-medium text-slate-800 text-sm">Generate Emergency Recovery Token</div>
          <Textarea
            placeholder="Reason for break-glass access (required for audit trail)…"
            value={reason}
            onChange={e => setReason(e.target.value)}
            rows={2}
          />
          {genError && <div className="text-xs text-red-600">{genError}</div>}
          <Button variant="subtle" onClick={generate} disabled={genLoading || !reason.trim()} loading={genLoading} className="!bg-amber-600 !text-white hover:!bg-amber-700">
            <Zap className="w-4 h-4" /> {genLoading ? "Generating…" : "Generate Recovery Token"}
          </Button>
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
              <Card key={e.id} padding="sm" className={e.used ? "" : "bg-amber-50"} accent={e.used ? undefined : AMBER}>
                <div className="flex justify-between mb-1 text-xs">
                  <span className="font-medium text-slate-700">{e.reason}</span>
                  <Badge variant={e.used ? "neutral" : "warning"} size="sm">
                    {e.used ? `Used: ${e.action}` : "Not used"}
                  </Badge>
                </div>
                <div className="text-slate-400 text-xs">{e.created_at ? new Date(e.created_at).toLocaleString() : "—"} · {e.actor_email}</div>
              </Card>
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
  useEffect(() => { fetch(); }, [severity, resolved, fetch]);

  const resolve = async (id) => {
    await api.post(`/admin/hardening/security-events/${id}/resolve`, { note: resolveNote });
    setResolvingId(null); setResolveNote(""); fetch();
  };

  const stats = data?.stats || {};
  const events = data?.events || [];

  const SEV_ACCENT = { critical: CRIMSON, high: "#f97316", medium: AMBER, low: "#3B82F6" };

  return (
    <div className="space-y-4">
      {/* Stats */}
      <StatGrid cols={4}>
        {["critical", "high", "medium", "low"].map(s => {
          const d = stats.by_severity?.[s] || {};
          return (
            <StatCard
              key={s}
              label={`${s.charAt(0).toUpperCase()}${s.slice(1)} unresolved`}
              value={d.unresolved || 0}
              sub={`${d.total || 0} total`}
            />
          );
        })}
      </StatGrid>

      {/* Filters */}
      <div className="flex gap-2 flex-wrap">
        <FormSelect value={severity} onChange={e => setSeverity(e.target.value)} wrapperClassName="!mb-0">
          <option value="">All Severities</option>
          {["critical", "high", "medium", "low"].map(s => <option key={s} value={s}>{s}</option>)}
        </FormSelect>
        <FormSelect
          value={resolved === undefined ? "" : String(resolved)}
          onChange={e => setResolved(e.target.value === "" ? undefined : e.target.value === "true")}
          wrapperClassName="!mb-0"
        >
          <option value="">All Events</option>
          <option value="false">Unresolved</option>
          <option value="true">Resolved</option>
        </FormSelect>
        <Button variant="subtle" onClick={fetch}>
          <RefreshCw className="w-3 h-3" /> Refresh
        </Button>
      </div>

      {/* Events list */}
      {loading ? (
        <div className="text-sm text-slate-400 animate-pulse">Loading events…</div>
      ) : events.length === 0 ? (
        <div className="text-center py-8 text-slate-400 text-sm">No security events found</div>
      ) : (
        <div className="space-y-2">
          {events.map(e => (
            <Card key={e.id} padding="sm" className={e.resolved ? "opacity-70" : ""}>
              <div className="flex items-start justify-between gap-2">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    {sevPill(e.severity)}
                    <span className="text-sm font-medium text-slate-800">{e.event_type}</span>
                    {e.resolved && <Badge variant="success" size="sm">resolved</Badge>}
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
                    <div className="flex gap-1 flex-shrink-0 items-start">
                      <Input
                        type="text"
                        placeholder="Resolution note"
                        value={resolveNote}
                        onChange={ev => setResolveNote(ev.target.value)}
                        size="sm"
                        wrapperClassName="w-32 !mb-0"
                      />
                      <Button variant="primary" size="sm" onClick={() => resolve(e.id)}>OK</Button>
                      <Button variant="ghost" size="sm" onClick={() => setResolvingId(null)}>✕</Button>
                    </div>
                  ) : (
                    <Button variant="link" size="sm" onClick={() => setResolvingId(e.id)} className="flex-shrink-0">
                      Resolve
                    </Button>
                  )
                )}
              </div>
            </Card>
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
  useEffect(() => { fetch(); }, [debouncedAction, fetch]);

  const { data: summary, fetch: fetchSummary } = useApi("/api/admin/hardening/audit/summary");
  useEffect(() => { fetchSummary(); }, [fetchSummary]);

  const events = data?.events || [];

  const columns = [
    { key: "action", label: "Action", render: (v) => <span className="font-mono text-slate-700">{v}</span> },
    { key: "actor_email", label: "Actor", render: (v) => v || "—" },
    { key: "ip", label: "IP", render: (v) => <span className="font-mono text-slate-400">{v || "—"}</span> },
    { key: "created_at", label: "When", render: (v) => v ? new Date(v).toLocaleString() : "—" },
  ];

  return (
    <div className="space-y-4">
      {/* Summary */}
      {summary && (
        <StatGrid cols={4}>
          <StatCard label="Events (24h)" value={summary.total_last_24h} />
          <StatCard label="Events (7d)" value={summary.total_last_7d} />
          <StatCard label="Login Events" value={summary.login_events_total} />
          <StatCard label="Unresolved Events" value={summary.unresolved_security_events} />
        </StatGrid>
      )}

      <div className="flex gap-2 items-start">
        <Input
          type="text"
          placeholder="Filter by action (e.g. auth.login)"
          value={action}
          onChange={e => setAction(e.target.value)}
          wrapperClassName="flex-1 !mb-0"
        />
        <Button variant="subtle" onClick={fetch} aria-label="Refresh">
          <RefreshCw className="w-4 h-4" />
        </Button>
      </div>

      <DataTable columns={columns} rows={events} loading={loading} />
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// TAB: Certification
// ─────────────────────────────────────────────────────────────────────────────
function CertificationTab() {
  const { data, loading, error, fetch } = useApi("/api/admin/hardening/certification");
  useEffect(() => { fetch(); }, [fetch]);

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

  return (
    <div className="space-y-6">
      {/* Overall score */}
      <Card accent={certified ? EMERALD : AMBER} padding="xl" className="text-center">
        <div className={`text-7xl font-black mb-1 ${grade_color === "green" ? "text-green-700" : grade_color === "lime" ? "text-lime-600" : grade_color === "yellow" ? "text-amber-600" : grade_color === "orange" ? "text-orange-600" : "text-red-700"}`}>
          {grade}
        </div>
        <div className="text-3xl font-bold text-slate-800 mb-2">{overall}/100</div>
        <Badge variant={certified ? "success" : "warning"} size="md">{certification_label}</Badge>
        <div className="text-xs text-slate-400 mt-2">Evaluated: {data.evaluated_at ? new Date(data.evaluated_at).toLocaleString() : "—"}</div>
      </Card>

      {/* Score breakdown */}
      <div className="space-y-3">
        {Object.entries(scores).map(([key, score]) => (
          <div key={key}>
            <ProgressBar
              label={SCORE_LABELS[key] || key}
              value={score}
              max={100}
              colorByValue
            />
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

      <Button variant="subtle" onClick={fetch} className="w-full justify-center">
        <RefreshCw className="w-4 h-4" /> Recalculate
      </Button>
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
      <div className="flex flex-col gap-4">
        {/* Tab bar */}
        <NavTabs tabs={TABS} active={tab} onChange={setTab} variant="underline" />

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
      </div>
    </AdministrationLayout>
  );
}
