/* eslint-disable */
import React, { useState, useCallback } from "react";
import {
  ShieldCheck, ShieldAlert, Shield, Users, RefreshCw,
  CheckCircle2, XCircle, AlertTriangle, Lock, Unlock,
  ChevronDown, ChevronRight, Zap, Eye,
} from "lucide-react";
import api from "@/lib/api";
import { NAVY, WARM, BRD } from "@/lib/tokens";
import { AdministrationLayout } from "@/layouts";
import { NavTabs, Card, Badge, Button, Alert, DataTable, StatCard, StatGrid } from "@/components/ds";

// ── tiny shared fetch hook ────────────────────────────────────────────────────
function useAdminFetch(path, deps = []) {
  const [data, setData]       = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError]     = useState(null);

  const fetch = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const r = await api.get(path);
      setData(r.data);
    } catch (e) {
      setError(e?.response?.data?.detail || "Request failed");
    } finally {
      setLoading(false);
    }
  }, deps);

  return { data, loading, error, fetch };
}

// ── colour helpers ────────────────────────────────────────────────────────────
const ROLE_VARIANT = {
  super_admin:         "danger",
  admin:               "danger",
  institution_admin:   "warning",
  moderator:           "info",
  verified_professor:  "purple",
  verified_researcher: "purple",
  user:                "neutral",
};
const rolePill = (role) => (
  <Badge variant={ROLE_VARIANT[role] || "neutral"}>{role}</Badge>
);

// ─────────────────────────────────────────────────────────────────────────────
// Section: Protected Account Status
// ─────────────────────────────────────────────────────────────────────────────
function ProtectedStatus() {
  const { data, loading, error, fetch } = useAdminFetch("/api/admin/account-security/protected-status");

  React.useEffect(() => { fetch(); }, []);

  if (loading) return <div className="text-sm text-slate-400 animate-pulse">Checking protected account…</div>;
  if (error)   return <div className="text-sm text-red-500">{error}</div>;
  if (!data)   return null;

  return (
    <Alert variant={data.healthy ? "success" : "error"} icon={data.healthy ? CheckCircle2 : XCircle}>
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <span className="font-semibold text-slate-800">
            {data.exists ? data.email : "Protected account not found"}
          </span>
          {data.exists && rolePill(data.role)}
        </div>
        <Button variant="link" size="sm" onClick={fetch}>
          <RefreshCw className="w-3 h-3" /> Refresh
        </Button>
      </div>

      {data.exists && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-sm">
          <div>
            <div className="text-slate-500 text-xs">Status</div>
            <div className={`font-medium ${data.status === "active" ? "text-green-700" : "text-red-700"}`}>
              {data.status}
            </div>
          </div>
          <div>
            <div className="text-slate-500 text-xs">Email verified</div>
            <div className={`font-medium ${data.email_verified ? "text-green-700" : "text-red-700"}`}>
              {data.email_verified ? "Yes" : "No"}
            </div>
          </div>
          <div>
            <div className="text-slate-500 text-xs">Protected flag</div>
            <div className={`font-medium ${data.protected ? "text-green-700" : "text-amber-700"}`}>
              {data.protected ? "Set" : "Missing"}
            </div>
          </div>
          <div>
            <div className="text-slate-500 text-xs">Plan</div>
            <div className="font-medium text-slate-700">{data.plan_code || "—"}</div>
          </div>
        </div>
      )}

      {data.issues?.length > 0 && (
        <div className="mt-3 space-y-1">
          {data.issues.map((issue, i) => (
            <div key={i} className="flex items-center gap-2 text-sm text-red-700">
              <AlertTriangle className="w-3.5 h-3.5 flex-shrink-0" />
              {issue}
            </div>
          ))}
        </div>
      )}
    </Alert>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Section: Role Hierarchy
// ─────────────────────────────────────────────────────────────────────────────
function RoleHierarchy() {
  const { data, loading, fetch } = useAdminFetch("/api/admin/account-security/role-hierarchy");
  React.useEffect(() => { fetch(); }, []);

  if (loading) return <div className="text-sm text-slate-400 animate-pulse">Loading hierarchy…</div>;
  if (!data)   return null;

  return (
    <div className="space-y-2">
      {(data.hierarchy || []).map((row) => (
        <div key={row.role} className="flex items-center gap-3">
          <div className="w-8 text-right text-xs font-mono text-slate-400">L{Math.round(row.level / 10)}</div>
          <div className="flex-1 flex items-center gap-2">
            {/* Kept as a raw gradient bar (not ds/ProgressBar): the red→blue
                gradient fill encoding hierarchy level has no equivalent in
                ProgressBar's single-color fill API. */}
            <div
              className="h-2 rounded-full bg-gradient-to-r from-red-400 to-blue-400"
              style={{ width: `${row.level}%`, opacity: 0.6 + row.level / 300 }}
            />
          </div>
          {rolePill(row.role)}
          <div className="w-16 text-right text-xs text-slate-500">{row.count.toLocaleString()} users</div>
          {row.role === "super_admin" && <Badge variant="danger" size="sm">DB-only</Badge>}
          {row.api_grantable && <Badge variant="neutral" size="sm">API</Badge>}
        </div>
      ))}
      <div className="text-xs text-slate-400 mt-1">Total platform users: {data.total_users?.toLocaleString()}</div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Section: Privilege Audit
// ─────────────────────────────────────────────────────────────────────────────
function PrivilegeAudit() {
  const { data, loading, error, fetch } = useAdminFetch("/api/admin/account-security/audit");
  React.useEffect(() => { fetch(); }, []);

  if (loading) return <div className="text-sm text-slate-400 animate-pulse">Auditing accounts…</div>;
  if (error)   return <div className="text-sm text-red-500">{error}</div>;
  if (!data)   return null;

  const accountColumns = [
    {
      key: "email", label: "Email",
      render: (v, row) => (
        <span className="flex items-center gap-1.5 font-mono text-xs">
          {v}
          {row.is_protected && <Lock className="w-3 h-3 text-green-600" title="Protected" />}
        </span>
      ),
    },
    { key: "role", label: "Role", render: (v) => rolePill(v) },
    {
      key: "status", label: "Status",
      render: (v) => <span className={`text-xs ${v === "active" ? "text-green-600" : "text-red-600"}`}>{v}</span>,
    },
    {
      key: "email_verified", label: "Verified", align: "center",
      render: (v) => v
        ? <CheckCircle2 className="w-4 h-4 text-green-500 inline" />
        : <XCircle className="w-4 h-4 text-slate-300 inline" />,
    },
    { key: "created_at", label: "Created", render: (v) => <span className="text-xs text-slate-500">{v}</span> },
    {
      key: "flags", label: "Flags",
      render: (_, row) => (
        <div className="flex gap-1 flex-wrap">
          {row.is_protected && <Badge variant="success" size="sm">protected</Badge>}
          {row.in_env_list && <Badge variant="info" size="sm">env-list</Badge>}
          {row.role === "super_admin" && !row.is_protected && <Badge variant="danger" size="sm">ROGUE</Badge>}
        </div>
      ),
    },
  ];

  return (
    <div className="space-y-4">
      {/* Risk banner */}
      {data.risk_count > 0 && (
        <Alert variant="error" icon={ShieldAlert} title={`${data.risk_count} security risk${data.risk_count > 1 ? "s" : ""} detected`}>
          {data.risks.map((r, i) => (
            <div key={i}>{r.message}</div>
          ))}
        </Alert>
      )}

      {/* Stats bar */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
        <Card padding="sm" className="text-center" style={{ background: "#f8fafc" }}>
          <div className="text-2xl font-bold text-slate-700">{data.total_elevated}</div>
          <div className="text-xs text-slate-500">Elevated accounts</div>
        </Card>
        <Card padding="sm" className="text-center" style={{ background: data.rogue_count > 0 ? "#fef2f2" : "#f0fdf4" }}>
          <div className={`text-2xl font-bold ${data.rogue_count > 0 ? "text-red-700" : "text-green-700"}`}>{data.rogue_count}</div>
          <div className={`text-xs ${data.rogue_count > 0 ? "text-red-500" : "text-green-500"}`}>Rogue super-admins</div>
        </Card>
        <Card padding="sm" className="text-center" style={{ background: data.protected_account_exists ? "#f0fdf4" : "#fef2f2" }}>
          <div className={`text-2xl font-bold ${data.protected_account_exists ? "text-green-700" : "text-red-700"}`}>
            {data.protected_account_exists ? "✓" : "✗"}
          </div>
          <div className={`text-xs ${data.protected_account_exists ? "text-green-500" : "text-red-500"}`}>Protected account</div>
        </Card>
      </div>

      {/* Account table */}
      {/* Note: the original per-row green tint for protected accounts (a subtle
          background highlight on the whole <tr>) isn't representable through
          DataTable's per-cell `render` API (no row-level style hook) — the
          Lock icon + "protected" badge in the Email/Flags columns still
          communicate the same status. */}
      <DataTable columns={accountColumns} rows={data.accounts || []} />

      <div className="text-xs text-slate-400">
        Audited at {data.audited_at ? new Date(data.audited_at).toLocaleString() : "—"}
        <Button variant="link" size="sm" onClick={fetch} className="ml-3">Refresh</Button>
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Section: Lockdown Panel
// ─────────────────────────────────────────────────────────────────────────────
function LockdownPanel() {
  const [dryResult, setDryResult]   = useState(null);
  const [applyResult, setApplyResult] = useState(null);
  const [loading, setLoading]       = useState(false);
  const [confirm, setConfirm]       = useState(false);

  const runDry = async () => {
    setLoading(true);
    try {
      const r = await api.post("/admin/account-security/lockdown?dry_run=true");
      setDryResult(r.data);
    } catch (e) {
      setDryResult({ error: e?.response?.data?.detail || "Failed" });
    } finally {
      setLoading(false);
    }
  };

  const runApply = async () => {
    setLoading(true);
    try {
      const r = await api.post("/admin/account-security/lockdown?dry_run=false");
      setApplyResult(r.data);
      setConfirm(false);
    } catch (e) {
      setApplyResult({ error: e?.response?.data?.detail || "Failed" });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-4">
      <p className="text-sm text-slate-600">
        The lockdown operation strips <code className="bg-slate-100 px-1 rounded">super_admin</code> from all accounts except <strong>admin@synaptiq.academy</strong>.
        Run a dry-run first to see what would be changed, then apply.
      </p>

      <div className="flex gap-3">
        <Button variant="subtle" onClick={runDry} disabled={loading}>
          <Eye className="w-4 h-4" /> Dry-run preview
        </Button>
        <Button variant="danger" onClick={() => setConfirm(true)} disabled={loading}>
          <Zap className="w-4 h-4" /> Apply lockdown
        </Button>
      </div>

      {/* Kept as inline content (not ds/Dialog): this confirmation flows
          in-page below the buttons rather than blocking the page behind a
          modal backdrop — swapping in Dialog would change that interaction,
          not just its styling. */}
      {confirm && (
        <Alert variant="error" title="Confirm lockdown">
          <p className="mb-3">
            This will demote ALL super_admin accounts except admin@synaptiq.academy to the "user" role.
            This action is audit-logged and irreversible via the API.
          </p>
          <div className="flex gap-2">
            <Button variant="danger" size="sm" onClick={runApply} loading={loading}>
              Yes, apply lockdown
            </Button>
            <Button variant="ghost" size="sm" onClick={() => setConfirm(false)}>
              Cancel
            </Button>
          </div>
        </Alert>
      )}

      {dryResult && (
        <Alert variant={dryResult.error ? "error" : "neutral"} title="Dry-run result">
          {dryResult.error ? (
            <div>{dryResult.error}</div>
          ) : (
            <>
              <div>Accounts that would be demoted: <strong>{dryResult.demoted_count}</strong></div>
              {dryResult.demoted_accounts?.map((a, i) => (
                <div key={i} className="font-mono text-xs ml-2">{a.email} → user</div>
              ))}
              {dryResult.demoted_count === 0 && (
                <div className="text-green-700 mt-1">Platform is already locked down. No changes needed.</div>
              )}
            </>
          )}
        </Alert>
      )}

      {applyResult && (
        <Alert variant={applyResult.error ? "error" : "success"} title={applyResult.error ? undefined : "Lockdown applied successfully"}>
          {applyResult.error ? (
            <div>{applyResult.error}</div>
          ) : (
            <>
              <div>{applyResult.demoted_count} account(s) demoted.</div>
              {applyResult.demoted_accounts?.map((a, i) => (
                <div key={i} className="font-mono text-xs ml-2">{a.email} → user</div>
              ))}
              <div className="mt-1">
                Protected account status: <strong>{applyResult.protected_status}</strong>
              </div>
            </>
          )}
        </Alert>
      )}
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Main page
// ─────────────────────────────────────────────────────────────────────────────
const TABS = ["overview", "audit", "lockdown", "hierarchy"];

export default function AdminAccountSecurity() {
  const [tab, setTab] = useState("overview");

  return (
    <AdministrationLayout title="Account Security" subtitle="Super-admin lockdown, privilege audit, and role hierarchy">
      {/* Quick status pill */}
      <div className="bg-slate-900 rounded-xl px-5 py-3 flex items-center gap-3 text-sm">
        <Lock className="w-4 h-4 text-green-400" />
        <span className="text-slate-300">Sole super-administrator:</span>
        <span className="font-mono text-green-400 font-semibold">admin@synaptiq.academy</span>
        <span className="text-slate-500 ml-auto text-xs">Cannot be deleted, suspended, or demoted via API</span>
      </div>

      {/* Tab bar */}
      <NavTabs
        tabs={TABS.map((t) => ({ id: t, label: t.charAt(0).toUpperCase() + t.slice(1) }))}
        active={tab}
        onChange={setTab}
      />

      {/* Tab content */}
      <div className="space-y-6">
        {tab === "overview" && (
          <>
            <section>
              <h2 className="text-sm font-semibold text-slate-700 mb-3 uppercase tracking-wide">Protected Account</h2>
              <ProtectedStatus />
            </section>

            <section>
              <h2 className="text-sm font-semibold text-slate-700 mb-3 uppercase tracking-wide">Security Controls</h2>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                {[
                  { label: "Suspend/Ban block",       desc: "API cannot suspend or ban the protected account." },
                  { label: "Delete block",             desc: "API cannot delete the protected account." },
                  { label: "Role demotion block",      desc: "Cannot change role of the protected account via API." },
                  { label: "API super_admin grant",    desc: "super_admin role cannot be granted via any API endpoint." },
                  { label: "Hierarchy enforcement",    desc: "Admins cannot modify users at equal or higher authority level." },
                  { label: "Seed-time auto-upgrade",   desc: "On restart, the protected account is automatically corrected to super_admin if tampered with." },
                ].map((c) => (
                  <Card key={c.label} padding="sm" className="flex gap-3">
                    <CheckCircle2 className="w-4 h-4 text-green-500 flex-shrink-0 mt-0.5" />
                    <div>
                      <div className="text-sm font-medium text-slate-800">{c.label}</div>
                      <div className="text-xs text-slate-500">{c.desc}</div>
                    </div>
                  </Card>
                ))}
              </div>
            </section>
          </>
        )}

        {tab === "audit" && (
          <section>
            <h2 className="text-sm font-semibold text-slate-700 mb-3 uppercase tracking-wide">Privilege Audit</h2>
            <PrivilegeAudit />
          </section>
        )}

        {tab === "lockdown" && (
          <section>
            <h2 className="text-sm font-semibold text-slate-700 mb-3 uppercase tracking-wide">Privilege Lockdown</h2>
            <LockdownPanel />
          </section>
        )}

        {tab === "hierarchy" && (
          <section>
            <h2 className="text-sm font-semibold text-slate-700 mb-3 uppercase tracking-wide">Role Hierarchy</h2>
            <Card padding="lg">
              <RoleHierarchy />
            </Card>
            <Alert variant="warning" className="mt-4">
              <strong>API grant restrictions:</strong> The <code className="bg-amber-100 px-1 rounded">super_admin</code> role
              cannot be granted via any API endpoint. It can only be assigned through the database seed script or direct
              database intervention. All other roles in the hierarchy are API-grantable by sufficiently privileged admins.
            </Alert>
          </section>
        )}
      </div>
    </AdministrationLayout>
  );
}
